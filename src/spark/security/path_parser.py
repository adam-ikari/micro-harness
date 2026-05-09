# src/spark/security/path_parser.py
"""Parse paths from shell commands."""

import logging
import os
import re
from typing import Optional

logger = logging.getLogger(__name__)


class PathParseCache:
    """Cache for path parsing results."""

    def __init__(self, max_size: int = 100):
        self.cache: dict[str, dict] = {}
        self.max_size = max_size

    def get(self, command: str) -> Optional[dict]:
        """Get cached parse result."""
        return self.cache.get(command)

    def set(self, command: str, result: dict) -> None:
        """Cache parse result."""
        if len(self.cache) >= self.max_size:
            # Remove oldest entry
            oldest = next(iter(self.cache))
            del self.cache[oldest]
        self.cache[command] = result


class PathParser:
    """Extract paths and operations from shell commands.

    Uses rule matching for common commands, LLM for complex cases.
    """

    # Command patterns: {command: (operation, arg_position)}
    # operation: 'read' or 'write'
    # arg_position: argument index containing path, None for optional, -1 for last
    COMMAND_PATTERNS = {
        # File reading
        "cat": ("read", 0),
        "less": ("read", 0),
        "more": ("read", 0),
        "head": ("read", 0),
        "tail": ("read", 0),

        # File writing
        "vim": ("write", 0),
        "nano": ("write", 0),
        "vi": ("write", 0),
        "rm": ("write", 0),
        "mkdir": ("write", 0),
        "touch": ("write", 0),
        "mv": ("write", 0),
        "cp": ("write", 0),  # Destination is write

        # Directory operations
        "ls": ("read", None),  # Optional path arg
        "cd": ("read", 0),
        "find": ("read", 0),

        # Git (usually safe in project dir)
        "git": ("read", None),

        # Package managers (write to system)
        "pip": ("write", None),
        "npm": ("write", None),
        "apt": ("write", None),
        "yum": ("write", None),
    }

    # Redirect patterns
    REDIRECT_PATTERNS = [
        (r">\s*(\S+)", "write"),      # > file
        (r">>\s*(\S+)", "write"),     # >> file
        (r"<\s*(\S+)", "read"),       # < file
    ]

    def __init__(self, llm=None):
        self.llm = llm
        self.cache = PathParseCache()

    def parse(self, command: str) -> list[tuple[str, str]]:
        """Parse command to extract paths and operations.

        Args:
            command: Shell command string

        Returns:
            List of (path, operation) tuples
        """
        # Check cache first
        cached = self.cache.get(command)
        if cached:
            return cached.get("results", [])

        # Try rule matching first
        results = self._parse_by_rules(command)

        # If rule matching failed and LLM available, use LLM
        if not results and self.llm:
            results = self._parse_by_llm(command)

        # Cache results
        self.cache.set(command, {"results": results})

        return results

    def _parse_by_rules(self, command: str) -> list[tuple[str, str]]:
        """Parse using predefined rules."""
        results = []

        # Check for redirects first
        for pattern, operation in self.REDIRECT_PATTERNS:
            matches = re.findall(pattern, command)
            for match in matches:
                results.append((match, operation))

        # Parse command and arguments
        parts = command.split()
        if not parts:
            return results

        cmd = parts[0]

        # Check if command is in patterns
        if cmd in self.COMMAND_PATTERNS:
            operation, arg_pos = self.COMMAND_PATTERNS[cmd]

            if arg_pos is None:
                # Optional path argument or system command
                # For system commands like pip/apt, treat as write
                if cmd in ("pip", "npm", "apt", "yum"):
                    results.append(("system", "write"))
                elif len(parts) > 1 and not parts[1].startswith("-"):
                    path = parts[1]
                    results.append((path, operation))
            elif arg_pos == -1:
                # Last argument
                if len(parts) > 1:
                    path = parts[-1]
                    results.append((path, operation))
            elif arg_pos < len(parts):
                # Specific position
                path = parts[arg_pos]
                results.append((path, operation))

        return results

    def _parse_by_llm(self, command: str) -> list[tuple[str, str]]:
        """Parse using LLM for complex commands."""
        if not self.llm:
            return []

        prompt = f"""Analyze this shell command and extract file paths and their operations.

Command: {command}

For each path, determine if it's a 'read' or 'write' operation.
- read: viewing, reading, listing files
- write: creating, modifying, deleting files

Output format (one per line):
path|operation

Example output:
/home/user/file.txt|read
/home/user/output.txt|write

If no paths found, output: NONE"""

        try:
            response = self.llm.chat([{"role": "user", "content": prompt}])
            content = response.content.strip()

            if content == "NONE" or not content:
                return []

            results = []
            for line in content.split("\n"):
                if "|" in line:
                    parts = line.split("|")
                    if len(parts) >= 2:
                        path = parts[0].strip()
                        operation = parts[1].strip().lower()
                        if operation in ("read", "write"):
                            results.append((path, operation))

            return results
        except Exception as e:
            logger.warning(f"LLM path parsing failed: {e}")
            return []