# src/zero_agent/security/risk_detector.py
"""Risk detection for dangerous operations."""

from zero_agent.config import SecurityConfig


class RiskDetector:
    """Risk detector for identifying dangerous commands."""

    def __init__(self, config: SecurityConfig):
        self.blocked_commands = config.blocked_commands
        self.confirm_patterns = config.confirm_patterns

    def is_blocked(self, command: str) -> bool:
        """Check if command is blocked.

        Args:
            command: 要检查的命令

        Returns:
            bool: 是否被禁止
        """
        for blocked in self.blocked_commands:
            if blocked in command:
                return True
        return False

    def needs_confirm(self, command: str) -> bool:
        """Check if command needs confirmation.

        Args:
            command: 要检查的命令

        Returns:
            bool: 是否需要确认
        """
        for pattern in self.confirm_patterns:
            if pattern in command:
                return True
        return False
