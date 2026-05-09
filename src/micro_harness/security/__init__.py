# src/micro_harness/security/__init__.py
"""Security module for zero-agent."""

from micro_harness.security.permission import PermissionManager, Decision
from micro_harness.security.risk_detector import RiskDetector
from micro_harness.security.path_trust import PathTrustManager
from micro_harness.security.path_parser import PathParser
from micro_harness.security.command import CommandParser, RiskLevel
from micro_harness.config import SecurityConfig


class SecurityManager:
    """Security manager integrating permission control and risk detection."""

    def __init__(self, config: SecurityConfig, yolo: bool = False):
        self.yolo = yolo
        self.permissions = PermissionManager(config)
        self.risk_detector = RiskDetector(config)

    def check(self, tool_name: str, args: dict) -> Decision:
        """Check if tool call is allowed.

        Args:
            tool_name: Tool name
            args: Tool arguments

        Returns:
            Decision: ALLOW / DENY / CONFIRM
        """
        command = args.get("command", "")

        # Blocked commands always denied
        if self.risk_detector.is_blocked(command):
            return Decision.DENY

        if self.yolo:
            # YOLO mode: only confirm high-risk
            if self.risk_detector.needs_confirm(command):
                return Decision.CONFIRM
            return Decision.ALLOW

        # Normal mode: check permissions + risk
        if self.risk_detector.needs_confirm(command):
            return Decision.CONFIRM

        return self.permissions.check(tool_name, args)


__all__ = [
    "Decision",
    "SecurityManager",
    "PermissionManager",
    "RiskDetector",
    "PathTrustManager",
    "PathParser",
    "CommandParser",
    "RiskLevel",
]
