# src/micro_harness/security/permission.py
"""Permission management for tool execution."""

from enum import Enum

from micro_harness.config import SecurityConfig


class Decision(Enum):
    """Security decision result."""
    ALLOW = "allow"
    DENY = "deny"
    CONFIRM = "confirm"


class PermissionManager:
    """Permission manager for tool execution."""

    def __init__(self, config: SecurityConfig):
        self.permissions = config.permissions

    def check(self, tool_name: str, args: dict) -> Decision:
        """Check tool call permission.

        Args:
            tool_name: Tool name
            args: Tool arguments

        Returns:
            Decision: Permission decision result
        """
        perm = self.permissions.get(tool_name, "confirm")

        if perm == "allow":
            return Decision.ALLOW
        elif perm == "deny":
            return Decision.DENY
        else:
            return Decision.CONFIRM
