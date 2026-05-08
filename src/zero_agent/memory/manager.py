# src/zero_agent/memory/manager.py
"""Memory management with Markdown persistence."""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional


class MemoryManager:
    """Manage conversation memory with Markdown persistence.

    Features:
    - Extract important content during compression
    - Persist as Markdown
    - Semantic deduplication
    - Layered loading (summary always, details on-demand)
    """

    def __init__(self, memory_path: str = "./.zero-agent/memory.md", llm=None):
        self.memory_path = Path(memory_path)
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        self.llm = llm

        # Initialize file if not exists
        if not self.memory_path.exists():
            self._init_memory_file()

    def _init_memory_file(self):
        """Initialize empty memory file."""
        content = """# Zero Agent Memory

## Summary
(Always loaded - key facts and decisions)

## Details
(Loaded on demand - full conversation history)

"""
        self.memory_path.write_text(content)

    def load_summary(self) -> str:
        """Load summary section (always loaded).

        Returns:
            str: Summary section content
        """
        if not self.memory_path.exists():
            return ""

        content = self.memory_path.read_text()

        # Extract summary section
        summary_match = re.search(r"## Summary\n(.*?)(?=\n## |$)", content, re.DOTALL)
        if summary_match:
            return summary_match.group(1).strip()
        return ""

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

    def append_to_summary(self, content: str, timestamp: bool = True):
        """Append to summary section.

        Args:
            content: Content to append
            timestamp: Whether to add timestamp
        """
        if not self.memory_path.exists():
            self._init_memory_file()

        existing = self.memory_path.read_text()

        # Add timestamp if requested
        if timestamp:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            content = f"- [{ts}] {content}"

        # Find and update summary section
        summary_match = re.search(r"(## Summary\n)", existing)
        if summary_match:
            insert_pos = summary_match.end()
            new_content = existing[:insert_pos] + content + "\n" + existing[insert_pos:]
            self.memory_path.write_text(new_content)

    def append_to_details(self, content: str, session_id: Optional[str] = None):
        """Append to details section.

        Args:
            content: Content to append
            session_id: Optional session identifier
        """
        if not self.memory_path.exists():
            self._init_memory_file()

        existing = self.memory_path.read_text()

        # Add session header if provided
        if session_id:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            content = f"\n### Session {session_id} ({ts})\n\n{content}"

        # Find and update details section
        details_match = re.search(r"(## Details\n)", existing)
        if details_match:
            insert_pos = details_match.end()
            new_content = existing[:insert_pos] + content + "\n" + existing[insert_pos:]
            self.memory_path.write_text(new_content)

    def deduplicate(self) -> None:
        """Semantic deduplication using LLM.

        Remove duplicate or similar entries.
        """
        if not self.llm:
            return

        summary = self.load_summary()
        if not summary:
            return

        prompt = f"""Analyze these memory entries and remove duplicates or very similar entries.

Current entries:
{summary}

Output the deduplicated entries, one per line, starting with "- ".
Keep the most recent/relevant version of duplicate entries.
If all entries are unique, output them unchanged."""

        try:
            response = self.llm.chat([{"role": "user", "content": prompt}])
            new_summary = response.content.strip()

            # Update summary section
            existing = self.memory_path.read_text()
            new_content = re.sub(
                r"## Summary\n.*?(?=\n## |$)",
                f"## Summary\n{new_summary}\n",
                existing,
                flags=re.DOTALL
            )
            self.memory_path.write_text(new_content)
        except Exception:
            pass

    def save_session(self, session_summary: str, important_facts: list[str] = None):
        """Save session summary on exit.

        Args:
            session_summary: Summary of the session
            important_facts: List of important facts to remember
        """
        # Save important facts to summary
        if important_facts:
            for fact in important_facts:
                self.append_to_summary(fact)

        # Save full session to details
        ts = datetime.now().strftime("%Y-%m-%d")
        self.append_to_details(session_summary, session_id=ts)

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

    def get_context_for_llm(self, include_details: bool = False) -> str:
        """Get memory context for LLM.

        Args:
            include_details: Whether to include details section

        Returns:
            str: Memory context string
        """
        summary = self.load_summary()
        if not summary:
            return ""

        context = f"[Memory Summary]\n{summary}"

        if include_details:
            details = self.load_details()
            if details:
                context += f"\n\n[Memory Details]\n{details[:1000]}"  # Limit details length

        return context
