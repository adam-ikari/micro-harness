# src/spark/security/command.py
"""Command security utilities."""

import shlex
from enum import Enum
from typing import Optional


class RiskLevel(Enum):
    """Risk level for commands."""
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Dangerous command patterns
DANGEROUS_PATTERNS = {
    # Critical - system destruction
    "rm -rf /": RiskLevel.CRITICAL,
    "rm -rf /*": RiskLevel.CRITICAL,
    "mkfs": RiskLevel.CRITICAL,
    "dd if=/dev/zero": RiskLevel.CRITICAL,
    "dd if=/dev/random": RiskLevel.CRITICAL,
    ":(){ :|:& };:": RiskLevel.CRITICAL,  # Fork bomb

    # High - data loss
    "rm -rf": RiskLevel.HIGH,
    "rmdir -p /": RiskLevel.HIGH,
    "shred": RiskLevel.HIGH,
    "wipefs": RiskLevel.HIGH,

    # Medium - system modification
    "chmod -R 777": RiskLevel.MEDIUM,
    "chown -R": RiskLevel.MEDIUM,
}

# Write command patterns (detected by command name)
WRITE_COMMANDS = {
    # File write (with redirect)
    "tee",
    # File operations
    "mv", "cp", "rm", "rmdir", "mkdir", "touch", "truncate",
    # Permissions
    "chmod", "chown", "chgrp",
    # Package management
    "pip", "npm", "yarn", "apt", "yum", "dnf", "pacman",
    # Git write operations
    "git-push", "git-commit",
    # Network write
    "curl-post", "curl-put", "curl-delete", "wget",
}

# Safe commands (read-only, no code execution)
SAFE_COMMANDS = {
    # File listing
    "ls", "dir", "head", "tail", "less", "more",
    # Search
    "grep", "egrep", "fgrep", "rg", "ag",
    # File location
    "find", "locate", "which", "whereis",
    # System info
    "pwd", "whoami", "id", "uname", "hostname",
    # Version control (read operations)
    "git", "svn", "hg",
    # File content (read-only)
    "cat",
}

# Note: echo, printf, python, node, ruby, perl are NOT in SAFE_COMMANDS
# because they can execute arbitrary code or write files


class CommandParser:
    """Parse and analyze shell commands."""

    def __init__(self, max_length: int = 4096):
        self.max_length = max_length

    def parse(self, command: str) -> tuple[Optional[str], list[str], dict]:
        """Parse command into components.

        Returns:
            tuple: (command_name, args, metadata)
        """
        if not command or not command.strip():
            return None, [], {"error": "empty command"}

        # Length check
        if len(command) > self.max_length:
            return None, [], {"error": f"command too long (max {self.max_length})"}

        # Try to parse with shlex
        try:
            parts = shlex.split(command)
        except ValueError as e:
            return None, [], {"error": f"parse error: {e}"}

        if not parts:
            return None, [], {"error": "empty command"}

        cmd_name = parts[0]
        args = parts[1:]

        # Detect redirects and pipes
        has_redirect = any(p in command for p in [">", ">>", "<"])
        has_pipe = "|" in command
        has_append = ">>" in command

        return cmd_name, args, {
            "has_redirect": has_redirect,
            "has_pipe": has_pipe,
            "has_append": has_append,
            "raw": command,
        }

    def is_write_operation(self, command: str) -> bool:
        """Check if command performs write operation.

        Args:
            command: Command string

        Returns:
            bool: True if write operation
        """
        cmd_name, args, meta = self.parse(command)

        if not cmd_name:
            return False

        # Redirect implies write
        if meta.get("has_redirect"):
            # Check if it's write redirect (>) vs read redirect (<)
            if ">" in command:
                return True

        # Check command name
        # Handle git specially
        if cmd_name == "git" and args:
            git_cmd = args[0]
            if git_cmd in ("push", "commit", "reset", "checkout", "branch", "tag"):
                return True
            return False

        # Handle curl specially
        if cmd_name == "curl" and args:
            if any(a in args for a in ["-X", "--request"]):
                # Find the method
                for i, a in enumerate(args):
                    if a in ("-X", "--request") and i + 1 < len(args):
                        method = args[i + 1].upper()
                        if method in ("POST", "PUT", "DELETE", "PATCH"):
                            return True
            return False

        # Check against write commands
        return cmd_name in WRITE_COMMANDS

    def get_risk_level(self, command: str) -> RiskLevel:
        """Assess risk level of command.

        Args:
            command: Command string

        Returns:
            RiskLevel: Assessed risk level
        """
        # Check dangerous patterns first
        for pattern, level in DANGEROUS_PATTERNS.items():
            if pattern in command:
                return level

        cmd_name, args, meta = self.parse(command)

        if not cmd_name:
            return RiskLevel.SAFE

        # Write operations are medium risk
        if self.is_write_operation(command):
            return RiskLevel.MEDIUM

        # Known safe commands
        if cmd_name in SAFE_COMMANDS and not meta.get("has_redirect"):
            return RiskLevel.SAFE

        # Unknown commands are low risk by default
        return RiskLevel.LOW

    def validate(self, command: str) -> tuple[bool, str]:
        """Validate command for execution.

        Args:
            command: Command string

        Returns:
            tuple: (is_valid, error_message)
        """
        cmd_name, args, meta = self.parse(command)

        if meta.get("error"):
            return False, meta["error"]

        # Block critical risk
        risk = self.get_risk_level(command)
        if risk == RiskLevel.CRITICAL:
            return False, f"blocked: critical risk command"

        return True, ""
