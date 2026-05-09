# src/zero_agent/builtin/shell.py
"""Cross-platform command execution using Python.

All operations use Python's pathlib, shutil, and os modules.
No shell dependency - consistent behavior across Windows/Linux/macOS.
"""

import logging
from typing import Any, Optional

from zero_agent.security.command import CommandParser, RiskLevel
from zero_agent.fs.operations import FileSystemOperations

logger = logging.getLogger(__name__)

# Security limits
MAX_COMMAND_LENGTH = 4096


class ShellResult(dict):
    """Typed result for command execution."""

    success: bool
    stdout: str
    stderr: str
    returncode: int
    error: Optional[str]


def get_tool_definition() -> dict[str, Any]:
    """Get tool definition for LLM.

    Returns:
        dict: Tool definition with name, description, parameters
    """
    return {
        "name": "run_shell",
        "description": "Execute file system command. Pure Python implementation, cross-platform.",
        "parameters": {
            "command": {
                "type": "string",
                "description": "Command to execute (ls, cat, cp, mv, rm, mkdir, touch, find, grep, pwd, which)",
            },
        },
    }


def validate_command(command: str) -> tuple[bool, str]:
    """Validate command before execution.

    Args:
        command: Command string to validate

    Returns:
        tuple: (is_valid, error_message)
    """
    if not command:
        return False, "Empty command"

    if not command.strip():
        return False, "Empty command"

    # Length check
    if len(command) > MAX_COMMAND_LENGTH:
        return False, f"Command too long (max {MAX_COMMAND_LENGTH} chars)"

    # Use command parser for risk assessment
    parser = CommandParser(max_length=MAX_COMMAND_LENGTH)
    is_valid, error = parser.validate(command)

    if not is_valid:
        return False, error

    return True, ""


def execute_python(command: str) -> ShellResult:
    """Execute command using Python implementation (cross-platform).

    Args:
        command: Command to execute

    Returns:
        ShellResult: Result
    """
    parser = CommandParser()
    cmd_name, args, meta = parser.parse(command)

    if not cmd_name:
        return ShellResult({
            "success": False,
            "stdout": "",
            "stderr": "",
            "returncode": -1,
            "error": "Empty command",
        })

    fs = FileSystemOperations()
    output = ""

    try:
        # File operations using Python
        if cmd_name in ("ls", "dir"):
            all_files = "-a" in args or "--all" in args
            long_fmt = "-l" in args or "/w" not in args
            path = args[0] if args and not args[0].startswith("-") else "."
            result = fs.list_dir(path, all_files, long_fmt)
            output = "\n".join(result)

        elif cmd_name in ("cat", "type"):
            if not args:
                return ShellResult({
                    "success": False, "stdout": "", "stderr": "",
                    "returncode": -1, "error": "Missing file path",
                })
            output = fs.read_file(args[0])

        elif cmd_name == "head":
            lines = 10
            if "-n" in args:
                idx = args.index("-n")
                if idx + 1 < len(args):
                    lines = int(args[idx + 1])
            path = [a for a in args if not a.startswith("-")][0]
            output = fs.read_file(path, lines=lines)

        elif cmd_name == "tail":
            lines = 10
            if "-n" in args:
                idx = args.index("-n")
                if idx + 1 < len(args):
                    lines = int(args[idx + 1])
            path = [a for a in args if not a.startswith("-")][0]
            output = fs.read_file(path, lines=lines, tail=True)

        elif cmd_name in ("cp", "copy"):
            if len(args) < 2:
                return ShellResult({
                    "success": False, "stdout": "", "stderr": "",
                    "returncode": -1, "error": "Missing source or destination",
                })
            recursive = "-r" in args or "-R" in args
            src = [a for a in args if not a.startswith("-")][0]
            dst = [a for a in args if not a.startswith("-")][1]
            output = fs.copy(src, dst, recursive)

        elif cmd_name in ("mv", "move"):
            if len(args) < 2:
                return ShellResult({
                    "success": False, "stdout": "", "stderr": "",
                    "returncode": -1, "error": "Missing source or destination",
                })
            src = [a for a in args if not a.startswith("-")][0]
            dst = [a for a in args if not a.startswith("-")][1]
            output = fs.move(src, dst)

        elif cmd_name in ("rm", "del"):
            if not args:
                return ShellResult({
                    "success": False, "stdout": "", "stderr": "",
                    "returncode": -1, "error": "Missing path",
                })
            recursive = "-r" in args or "-R" in args or "-rf" in args
            path = [a for a in args if not a.startswith("-")][0]
            output = fs.remove(path, recursive)

        elif cmd_name in ("mkdir", "md"):
            if not args:
                return ShellResult({
                    "success": False, "stdout": "", "stderr": "",
                    "returncode": -1, "error": "Missing path",
                })
            parents = "-p" in args
            path = [a for a in args if not a.startswith("-")][0]
            output = fs.make_dir(path, parents)

        elif cmd_name == "touch":
            if not args:
                return ShellResult({
                    "success": False, "stdout": "", "stderr": "",
                    "returncode": -1, "error": "Missing path",
                })
            output = fs.touch(args[0])

        elif cmd_name in ("pwd", "cd") and len(args) == 0:
            output = fs.pwd()

        elif cmd_name in ("which", "where"):
            if not args:
                return ShellResult({
                    "success": False, "stdout": "", "stderr": "",
                    "returncode": -1, "error": "Missing command name",
                })
            result = fs.which(args[0])
            output = result if result else f"{args[0]} not found"

        elif cmd_name == "find":
            path = "."
            name = None
            for i, a in enumerate(args):
                if a == "-name" and i + 1 < len(args):
                    name = args[i + 1]
                elif not a.startswith("-"):
                    path = a
            results = fs.find(path, name)
            output = "\n".join(results) if results else "No files found"

        elif cmd_name == "grep":
            if len(args) < 2:
                return ShellResult({
                    "success": False, "stdout": "", "stderr": "",
                    "returncode": -1, "error": "Missing pattern or path",
                })
            ignore_case = "-i" in args
            pattern = [a for a in args if not a.startswith("-")][0]
            path = [a for a in args if not a.startswith("-")][1]
            results = fs.grep(pattern, path, ignore_case)
            output = "\n".join(results)

        else:
            # Unknown command for Python implementation
            return ShellResult({
                "success": False,
                "stdout": "",
                "stderr": "",
                "returncode": -1,
                "error": f"Command '{cmd_name}' not supported in Python mode. Use shell mode.",
            })

        # Check if output is an error
        if output.startswith("Error:"):
            return ShellResult({
                "success": False,
                "stdout": "",
                "stderr": output,
                "returncode": 1,
                "error": output,
            })

        return ShellResult({
            "success": True,
            "stdout": output,
            "stderr": "",
            "returncode": 0,
            "error": None,
        })

    except Exception as e:
        return ShellResult({
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "returncode": -1,
            "error": str(e),
        })


def execute(command: str) -> ShellResult:
    """Execute command using Python implementation (cross-platform).

    All operations use Python's pathlib, shutil, and os modules.
    No shell dependency - consistent behavior across platforms.

    Args:
        command: Command to execute

    Returns:
        ShellResult: Result with success, stdout, stderr, returncode, error
    """
    # Validate command
    is_valid, error = validate_command(command)
    if not is_valid:
        return ShellResult({
            "success": False,
            "stdout": "",
            "stderr": "",
            "returncode": -1,
            "error": f"Validation error: {error}",
        })

    # Always use Python implementation for cross-platform consistency
    return execute_python(command)
