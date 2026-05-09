# src/micro_harness/history.py
"""Conversation history management with aggressive compression for small models."""

from dataclasses import dataclass, field
from typing import Any, Optional

from micro_harness.config import HistoryConfig


@dataclass
class HistoryManager:
    """Conversation history manager with aggressive compression support."""

    config: HistoryConfig
    messages: list[dict] = field(default_factory=list)
    memory_manager: Optional[Any] = None  # MemoryManager instance

    def set_memory_manager(self, memory_manager: Any) -> None:
        """Set memory manager for persistence."""
        self.memory_manager = memory_manager

    def add(self, role: str, content: str, **kwargs: Any) -> None:
        """Add message to history."""
        message = {"role": role, "content": content}
        message.update(kwargs)
        self.messages.append(message)

    def get_messages(self) -> list[dict]:
        """Get all messages."""
        return self.messages.copy()

    def clear(self) -> None:
        """Clear history."""
        self.messages.clear()

    def get_token_count(self) -> int:
        """Estimate current history token count."""
        total_chars = 0
        for msg in self.messages:
            content = msg.get("content", "")
            total_chars += len(content) + 15  # Message format overhead
        return int(total_chars * 0.3)

    def should_compress(self) -> bool:
        """Check if compression is needed.

        More aggressive: compress at 50% of max_tokens.
        """
        current_tokens = self.get_token_count()
        threshold = self.config.max_tokens * 0.5  # More aggressive
        return current_tokens >= threshold

    def compress(self, llm: Any) -> None:
        """Aggressive compression with summary chain.

        Strategy:
        - Keep last 2 rounds (4 messages) full
        - Compress middle messages to one-line summary
        - Extract key facts to memory
        """
        if len(self.messages) < 6:  # Need at least 6 messages
            return

        # Keep last 2 rounds (4 messages)
        old_messages = self.messages[:-4]
        recent_messages = self.messages[-4:]

        if not old_messages:
            return

        # Generate compact summary
        summary = self._generate_compact_summary(llm, old_messages)

        # Extract important content to memory
        if self.memory_manager:
            self._extract_to_memory(llm, old_messages)

        # Replace old messages with compact summary
        self.messages = [
            {"role": "system", "content": f"[Summary]\n{summary}"},
            *recent_messages,
        ]

    def _generate_compact_summary(self, llm: Any, messages: list[dict]) -> str:
        """Generate very compact summary.

        Args:
            llm: LLM adapter
            messages: Messages to summarize

        Returns:
            str: Compact summary
        """
        # Build minimal context for summary
        lines = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            # Truncate to essential info
            if len(content) > 100:
                content = content[:100] + "..."
            lines.append(f"{role[0]}: {content}")  # u: or a:

        context = "\n".join(lines)

        # Use LLM to extract key facts if available
        if hasattr(llm, 'extract_facts') and callable(getattr(llm, 'extract_facts')):
            try:
                facts = llm.extract_facts(context)
                if facts and isinstance(facts, list):
                    return "\n".join(f"- {f}" for f in facts[:5])
            except (TypeError, AttributeError):
                pass

        # Fallback: simple summary
        try:
            summary = llm.generate_summary(messages)
            return summary[:300] if summary else "No summary"
        except (TypeError, AttributeError):
            return "Previous conversation"

    def _extract_to_memory(self, llm: Any, messages: list[dict]) -> None:
        """Extract important facts to memory.

        Args:
            llm: LLM adapter
            messages: Messages to extract from
        """
        if not self.memory_manager:
            return

        # Use LLM extraction if available
        if hasattr(llm, 'extract_facts'):
            content = "\n".join(m.get("content", "") for m in messages)
            facts = llm.extract_facts(content)
            for fact in facts[:3]:  # Limit to 3 facts
                self.memory_manager.append_to_index(fact)

    def save_to_memory(self) -> None:
        """Save current session to memory."""
        if not self.memory_manager:
            return

        # Build compact session summary
        lines = []
        for msg in self.messages[-6:]:  # Last 6 messages
            role = msg.get("role", "unknown")[0]  # First char
            content = msg.get("content", "")[:150]
            lines.append(f"{role}: {content}")

        session_summary = "\n".join(lines)
        self.memory_manager.save_session(session_summary)
