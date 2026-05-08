# src/zero_agent/history.py
"""Conversation history management with compression support."""

from dataclasses import dataclass, field
from typing import Any, Optional

from zero_agent.config import HistoryConfig


@dataclass
class HistoryManager:
    """Conversation history manager with summary compression support."""

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
            total_chars += len(content) + 20  # Message format overhead
        return int(total_chars * 0.3)

    def should_compress(self) -> bool:
        """Check if compression is needed."""
        current_tokens = self.get_token_count()
        threshold = self.config.max_tokens * self.config.compress_threshold
        return current_tokens >= threshold

    def compress(self, llm: Any) -> None:
        """Generate summary to replace old messages.

        Keep recent messages, compress old ones into summary.
        Also extract important content to memory.
        """
        if len(self.messages) < 4:
            return  # Too few messages, skip compression

        # Keep last 2 rounds (4 messages)
        old_messages = self.messages[:-4]
        recent_messages = self.messages[-4:]

        if not old_messages:
            return

        # Generate summary
        summary = llm.generate_summary(old_messages)

        # Extract important content to memory
        if self.memory_manager:
            important_facts = self.memory_manager.extract_important_content(old_messages)
            for fact in important_facts:
                self.memory_manager.append_to_summary(fact)

        # Replace old messages with summary
        self.messages = [
            {"role": "system", "content": f"[Previous conversation summary]\n{summary}"},
            *recent_messages,
        ]

    def save_to_memory(self) -> None:
        """Save current session to memory."""
        if not self.memory_manager:
            return

        # Build session summary
        session_summary = "\n".join([
            f"{msg.get('role', 'unknown')}: {msg.get('content', '')[:200]}"
            for msg in self.messages[-10:]  # Last 10 messages
        ])

        self.memory_manager.save_session(session_summary)
