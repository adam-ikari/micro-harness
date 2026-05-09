# src/zero_agent/memory/manager.py
"""Memory management with Markdown persistence optimized for small models."""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

# Token limits for small models
MAX_INDEX_TOKENS = 200  # ~800 chars
MAX_DETAIL_TOKENS = 500  # ~2000 chars


class MemoryManager:
    """Manage conversation memory with Markdown persistence.

    Optimized for small models:
    - Layered loading (index always, details on-demand)
    - Token-limited output
    - Keyword-based relevance matching
    """

    def __init__(self, memory_path: str = "./.zero-agent/memory.md", llm=None,
                 max_index_tokens: int = MAX_INDEX_TOKENS):
        self.memory_path = Path(memory_path)
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        self.llm = llm
        self.max_index_tokens = max_index_tokens

        # Initialize file if not exists
        if not self.memory_path.exists():
            self._init_memory_file()

    def _init_memory_file(self):
        """Initialize empty memory file with Markdown link structure."""
        content = """# Zero Agent Memory

## Index
Key facts with links to details:
- *Empty - add memories during conversation*

## Details
Full conversation history (loaded on demand):

<!-- Memory entries go here, linked from Index -->
"""
        self.memory_path.write_text(content)

    def load_index(self) -> str:
        """Load index section (always loaded).

        Returns:
            str: Index section content
        """
        if not self.memory_path.exists():
            return ""

        content = self.memory_path.read_text()

        # Extract index section
        index_match = re.search(r"## Index\n(.*?)(?=\n## |$)", content, re.DOTALL)
        if index_match:
            return index_match.group(1).strip()
        return ""

    def load_summary(self) -> str:
        """Load summary section (alias for load_index for backward compatibility).

        Returns:
            str: Index section content
        """
        return self.load_index()

    def load_details(self) -> str:
        """Load details section (on demand).

        Returns:
            str: Details section content
        """
        if not self.memory_path.exists():
            return ""

        content = self.memory_path.read_text()

        # Extract details section
        details_match = re.search(r"## Details\n(.*?)$", content, re.DOTALL)
        if details_match:
            return details_match.group(1).strip()
        return ""

    def append_to_index(self, content: str, detail_id: Optional[str] = None, timestamp: bool = True):
        """Append to index section with optional link to details.

        Args:
            content: Content to append (short summary)
            detail_id: Optional detail section ID to link
            timestamp: Whether to add timestamp
        """
        if not self.memory_path.exists():
            self._init_memory_file()

        existing = self.memory_path.read_text()

        # Add timestamp if requested
        if timestamp:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            content = f"- [{ts}] {content}"

        # Add link to details if provided
        if detail_id:
            content += f" [→详情](#{detail_id})"

        # Find and update index section
        index_match = re.search(r"(## Index\n)", existing)
        if index_match:
            insert_pos = index_match.end()
            new_content = existing[:insert_pos] + content + "\n" + existing[insert_pos:]
            self.memory_path.write_text(new_content)

    def append_to_summary(self, content: str, timestamp: bool = True):
        """Append to summary section (alias for backward compatibility).

        Args:
            content: Content to append
            timestamp: Whether to add timestamp
        """
        self.append_to_index(content, timestamp=timestamp)

    def append_to_details(self, content: str, session_id: Optional[str] = None) -> str:
        """Append to details section with anchor ID.

        Args:
            content: Content to append
            session_id: Optional session identifier

        Returns:
            str: Anchor ID for linking from index
        """
        if not self.memory_path.exists():
            self._init_memory_file()

        existing = self.memory_path.read_text()

        # Generate anchor ID
        anchor_id = f"detail-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        if session_id:
            anchor_id = f"session-{session_id}"

        # Add session header with anchor ID
        if session_id:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            content = f"\n<a id=\"{anchor_id}\"></a>\n### Session {session_id} ({ts})\n\n{content}"
        else:
            content = f"\n<a id=\"{anchor_id}\"></a>\n{content}"

        # Find and update details section
        details_match = re.search(r"(## Details\n)", existing)
        if details_match:
            insert_pos = details_match.end()
            new_content = existing[:insert_pos] + content + "\n" + existing[insert_pos:]
            self.memory_path.write_text(new_content)

        return anchor_id

    def deduplicate(self) -> None:
        """Semantic deduplication using LLM.

        Remove duplicate or similar entries.
        """
        if not self.llm:
            return

        index = self.load_index()
        if not index:
            return

        prompt = f"""Analyze these memory entries and remove duplicates or very similar entries.

Current entries:
{index}

Output the deduplicated entries, one per line, starting with "- ".
Keep the most recent/relevant version of duplicate entries.
Preserve any Markdown links [→详情](#...) in the entries.
If all entries are unique, output them unchanged."""

        try:
            response = self.llm.chat([{"role": "user", "content": prompt}])
            new_index = response.content.strip()

            # Update index section
            existing = self.memory_path.read_text()
            new_content = re.sub(
                r"## Index\n.*?(?=\n## |$)",
                f"## Index\n{new_index}\n",
                existing,
                flags=re.DOTALL
            )
            self.memory_path.write_text(new_content)
        except Exception:
            pass

    def save_session(self, session_summary: str, important_facts: list[str] = None):
        """Save session summary on exit with linked structure.

        Args:
            session_summary: Summary of the session
            important_facts: List of important facts to remember
        """
        # Save full session to details first, get anchor ID
        ts = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        anchor_id = self.append_to_details(session_summary, session_id=ts)

        # Save important facts to index with link to details
        if important_facts:
            for fact in important_facts:
                self.append_to_index(fact, detail_id=anchor_id)

        # Run deduplication
        self.deduplicate()

    def extract_important_content(self, messages: list[dict]) -> list[str]:
        """Extract important content from messages.

        Args:
            messages: List of conversation messages

        Returns:
            List of important facts/decisions
        """
        if not self.llm or not messages:
            return []

        # Build prompt for extraction
        conversation = "\n".join([
            f"{msg.get('role', 'unknown')}: {msg.get('content', '')}"
            for msg in messages
        ])

        prompt = f"""Extract important information from this conversation that should be remembered.

Conversation:
{conversation}

Important information includes:
- User decisions or preferences
- Key facts about the project
- Important results or outcomes
- Errors or issues encountered

Output format: One fact per line, starting with "- ".
If nothing important, output: NONE"""

        try:
            response = self.llm.chat([{"role": "user", "content": prompt}])
            content = response.content.strip()

            if content == "NONE" or not content:
                return []

            # Parse facts
            facts = []
            for line in content.split("\n"):
                line = line.strip()
                if line.startswith("- "):
                    facts.append(line[2:])
                elif line:
                    facts.append(line)

            return facts
        except Exception:
            return []

    def get_context_for_llm(self, include_details: bool = False,
                            max_tokens: int = MAX_INDEX_TOKENS) -> str:
        """Get memory context for LLM with token limit.

        Args:
            include_details: Whether to include details section
            max_tokens: Maximum tokens to return

        Returns:
            str: Memory context string (token-limited)
        """
        summary = self.load_summary()
        if not summary:
            return ""

        # Limit summary to max_tokens (4 chars ≈ 1 token)
        max_chars = max_tokens * 4
        if len(summary) > max_chars:
            summary = summary[:max_chars] + "..."

        context = f"[Memory]\n{summary}"

        if include_details:
            details = self.load_details()
            if details:
                # Limit details more aggressively
                detail_chars = min(MAX_DETAIL_TOKENS * 4, len(details))
                context += f"\n\n[Details]\n{details[:detail_chars]}"

        return context

    def get_relevant_context(self, user_input: str, max_tokens: int = 150) -> str:
        """Get memory context relevant to user input with strict token limit.

        Optimized for small models - only returns matching entries.

        Args:
            user_input: User's input text
            max_tokens: Maximum tokens to return

        Returns:
            str: Relevant memory context (or empty if not relevant)
        """
        if not self.should_load_memory(user_input):
            return ""

        # Get keywords from user input
        user_keywords = set(re.findall(r'\b[a-zA-Z]{3,}\b', user_input.lower()))

        # Filter memory entries by keyword match
        summary = self.load_summary()
        if not summary:
            return ""

        # Split into entries and filter
        entries = []
        for line in summary.split("\n"):
            if line.strip().startswith("- "):
                line_lower = line.lower()
                # Check if any user keyword matches
                if any(kw in line_lower for kw in user_keywords):
                    entries.append(line)

        if not entries:
            # No direct match, return top 3 entries
            entries = [l for l in summary.split("\n") if l.strip().startswith("- ")][:3]

        # Limit output
        result = "\n".join(entries[:5])  # Max 5 entries
        max_chars = max_tokens * 4

        if len(result) > max_chars:
            result = result[:max_chars] + "..."

        return f"[Memory]\n{result}" if result else ""

    def get_keywords(self) -> list[str]:
        """Extract keywords from memory for relevance matching.

        Returns:
            List of keywords
        """
        summary = self.load_summary()
        if not summary:
            return []

        # Simple keyword extraction: words that appear in summary
        # Skip common words
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                      "being", "have", "has", "had", "do", "does", "did", "will",
                      "would", "could", "should", "may", "might", "must", "shall",
                      "can", "need", "dare", "ought", "used", "to", "of", "in",
                      "for", "on", "with", "at", "by", "from", "as", "into",
                      "through", "during", "before", "after", "above", "below",
                      "between", "under", "again", "further", "then", "once", "and",
                      "but", "or", "nor", "so", "yet", "both", "either", "neither",
                      "not", "only", "own", "same", "than", "too", "very", "just"}

        words = re.findall(r'\b[a-zA-Z]{3,}\b', summary.lower())
        keywords = [w for w in words if w not in stop_words]

        # Return unique keywords, sorted by frequency
        from collections import Counter
        word_counts = Counter(keywords)
        return [w for w, _ in word_counts.most_common(20)]

    def should_load_memory(self, user_input: str) -> bool:
        """Check if memory should be loaded based on user input.

        Args:
            user_input: User's input text

        Returns:
            bool: True if memory should be loaded
        """
        # Quick keyword check first
        keywords = self.get_keywords()
        user_input_lower = user_input.lower()

        for kw in keywords:
            if kw in user_input_lower:
                return True

        # If LLM available, ask for relevance judgment
        if self.llm:
            return self._llm_check_relevance(user_input, keywords)

        return False

    def _llm_check_relevance(self, user_input: str, keywords: list[str]) -> bool:
        """Use LLM to check if memory is relevant to user input.

        Args:
            user_input: User's input text
            keywords: Available memory keywords

        Returns:
            bool: True if memory is relevant
        """
        if not keywords:
            return False

        prompt = f"""Determine if the user's question might need information from memory.

User question: {user_input}

Memory contains information about: {', '.join(keywords[:10])}

Answer YES if memory might be relevant, NO otherwise.
Answer only YES or NO."""

        try:
            response = self.llm.chat([{"role": "user", "content": prompt}])
            return "YES" in response.content.upper()
        except Exception:
            return False

    def get_relevant_context(self, user_input: str) -> str:
        """Get memory context relevant to user input.

        Args:
            user_input: User's input text

        Returns:
            str: Relevant memory context
        """
        if not self.should_load_memory(user_input):
            return ""

        return self.get_context_for_llm(include_details=False)
