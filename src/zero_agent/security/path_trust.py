# src/zero_agent/security/path_trust.py
"""Path trust management for zero-agent."""

import os
from typing import Optional

from zero_agent.security import Decision


class PathTrustManager:
    """Manage trusted paths for security checks.

    Only current directory can be trusted.
    Trust is not persisted - asked each session.
    """

    def __init__(self, trust_current_dir: bool = False):
        self.trusted_paths: set[str] = set()
        self.current_dir = os.getcwd()
        self._trust_current_dir = trust_current_dir

        if trust_current_dir:
            self.trusted_paths.add(self.current_dir)

    def ask_trust_current_dir(self) -> bool:
        """Ask user if they trust current directory.

        Returns:
            bool: True if user trusts, False otherwise
        """
        print(f"\n是否信任当前目录? {self.current_dir}")
        print("[y/N]: ", end="")
        try:
            response = input().strip().lower()
            if response == "y":
                self.trusted_paths.add(self.current_dir)
                return True
        except EOFError:
            pass
        return False

    def is_trusted(self, path: str) -> bool:
        """Check if path is trusted.

        Args:
            path: Path to check

        Returns:
            bool: True if path is trusted
        """
        try:
            abs_path = os.path.abspath(path)
            for trusted in self.trusted_paths:
                if abs_path.startswith(trusted):
                    return True
                # Check if path is under trusted directory
                if abs_path.startswith(trusted + os.sep):
                    return True
        except Exception:
            pass
        return False

    def check_path_permission(self, path: str, operation: str, mode: str) -> Decision:
        """Check path permission based on mode.

        Args:
            path: Path being accessed
            operation: 'read' or 'write'
            mode: 'plan', 'ask', or 'yolo'

        Returns:
            Decision: ALLOW, DENY, or CONFIRM
        """
        # Plan mode: read allowed, write denied
        if mode == "plan":
            if operation == "read":
                return Decision.ALLOW
            return Decision.DENY

        # Ask mode: read allowed, write needs confirm if not trusted
        if mode == "ask":
            if operation == "read":
                return Decision.ALLOW
            if self.is_trusted(path):
                return Decision.ALLOW
            return Decision.CONFIRM

        # Yolo mode: all allowed, but high-risk still needs confirm
        if mode == "yolo":
            if self.is_trusted(path):
                return Decision.ALLOW
            # Non-trusted path in yolo mode still needs confirm for writes
            if operation == "write":
                return Decision.CONFIRM
            return Decision.ALLOW

        return Decision.CONFIRM

    def add_trusted_path(self, path: str) -> None:
        """Add a path to trusted paths.

        Args:
            path: Path to trust
        """
        abs_path = os.path.abspath(path)
        self.trusted_paths.add(abs_path)

    def get_trusted_paths(self) -> list[str]:
        """Get list of trusted paths.

        Returns:
            List of trusted path strings
        """
        return list(self.trusted_paths)
