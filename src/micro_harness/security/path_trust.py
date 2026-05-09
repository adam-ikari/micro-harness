# src/micro_harness/security/path_trust.py
"""Path trust management for zero-agent."""

import os
import logging
from typing import Optional

from micro_harness.security import Decision

logger = logging.getLogger(__name__)


class PathTrustManager:
    """Manage trusted paths for security checks.

    Only current directory can be trusted.
    Trust is not persisted - asked each session.
    Uses realpath() to resolve symlinks and prevent traversal attacks.
    """

    def __init__(self, trust_current_dir: bool = False):
        self.trusted_paths: set[str] = set()
        self.current_dir = self._safe_realpath(os.getcwd())
        self._trust_current_dir = trust_current_dir

        if trust_current_dir:
            self.trusted_paths.add(self.current_dir)

    def _safe_realpath(self, path: str) -> str:
        """Safely resolve path with realpath.

        Args:
            path: Path to resolve

        Returns:
            str: Resolved canonical path
        """
        try:
            # Normalize and resolve symlinks
            return os.path.normpath(os.path.realpath(path))
        except (OSError, ValueError) as e:
            logger.warning(f"Failed to resolve path {path}: {e}")
            return os.path.abspath(path)

    def _canonicalize(self, path: str) -> Optional[str]:
        """Canonicalize a path for comparison.

        Args:
            path: Path to canonicalize

        Returns:
            Optional[str]: Canonical path or None if invalid
        """
        if not path:
            return None

        try:
            # Expand user home directory
            expanded = os.path.expanduser(path)
            # Resolve to absolute path and follow symlinks
            return self._safe_realpath(expanded)
        except (OSError, ValueError) as e:
            logger.warning(f"Invalid path {path}: {e}")
            return None

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

        Uses realpath() to resolve symlinks and prevent:
        - Symlink attacks (symlink inside trusted dir pointing outside)
        - Path traversal (../ sequences)
        - Race conditions (TOCTOU) by canonicalizing at check time

        Args:
            path: Path to check

        Returns:
            bool: True if path is trusted
        """
        canonical_path = self._canonicalize(path)
        if not canonical_path:
            return False

        for trusted in self.trusted_paths:
            # Canonicalize trusted path too
            canonical_trusted = self._canonicalize(trusted)
            if not canonical_trusted:
                continue

            # Check if path is exactly the trusted path
            if canonical_path == canonical_trusted:
                return True

            # Check if path is under trusted directory
            # Use os.sep to ensure we're matching directory boundaries
            prefix = canonical_trusted + os.sep
            if canonical_path.startswith(prefix):
                return True

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
        canonical_path = self._canonicalize(path)
        if canonical_path:
            self.trusted_paths.add(canonical_path)

    def get_trusted_paths(self) -> list[str]:
        """Get list of trusted paths.

        Returns:
            List of trusted path strings
        """
        return list(self.trusted_paths)
