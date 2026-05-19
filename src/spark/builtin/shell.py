# src/spark/builtin/shell.py
"""Shell emulator using Python - cross-platform, no real shell dependency.

Small models only need to learn one tool: run_shell.
All common commands are simulated using Python APIs.
"""

import logging
from typing import Any, Optional
from pathlib import Path

from spark.security.command import CommandParser
from spark.fs.operations import FileSystemOperations

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

    Compatible with Claude Code tool format.

    Returns:
        dict: Tool definition with name, description, parameters
    """
    return {
        "name": "Bash",
        "description": "Execute shell command. Cross-platform Python implementation.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Command: ls, cat, head, tail, cp, mv, rm, mkdir, touch, find, grep, pwd, which, search",
                },
            },
            "required": ["command"],
        },
    }


def validate_command(command: str) -> tuple[bool, str]:
    """Validate command before execution.

    Args:
        command: Command string to validate

    Returns:
        tuple: (is_valid, error_message)
    """
    if not command or not command.strip():
        return False, "Empty command"

    if len(command) > MAX_COMMAND_LENGTH:
        return False, f"Command too long (max {MAX_COMMAND_LENGTH} chars)"

    parser = CommandParser(max_length=MAX_COMMAND_LENGTH)
    is_valid, error = parser.validate(command)

    if not is_valid:
        return False, error

    return True, ""


def execute(command: str) -> ShellResult:
    """Execute command using Python implementation.

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
            long_fmt = "-l" in args
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
            path = [a for a in args if not a.startswith("-")][0] if args else "."
            output = fs.read_file(path, lines=lines)

        elif cmd_name == "tail":
            lines = 10
            if "-n" in args:
                idx = args.index("-n")
                if idx + 1 < len(args):
                    lines = int(args[idx + 1])
            path = [a for a in args if not a.startswith("-")][0] if args else "."
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

        elif cmd_name == "pwd":
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
            file_type = None
            skip_next = False
            for i, a in enumerate(args):
                if skip_next:
                    skip_next = False
                    continue
                if a == "-name" and i + 1 < len(args):
                    name = args[i + 1]
                    skip_next = True
                elif a == "-type" and i + 1 < len(args):
                    file_type = args[i + 1]
                    skip_next = True
                elif not a.startswith("-"):
                    path = a
            results = fs.find(path, name, file_type)
            output = "\n".join(results) if results else "No files found"

        elif cmd_name == "grep":
            if len(args) < 2:
                return ShellResult({
                    "success": False, "stdout": "", "stderr": "",
                    "returncode": -1, "error": "Missing pattern or path",
                })
            ignore_case = "-i" in args
            recursive = "-r" in args or "-R" in args
            line_numbers = "-n" in args
            count_only = "-c" in args
            invert = "-v" in args
            pattern = [a for a in args if not a.startswith("-")][0]
            path = [a for a in args if not a.startswith("-")][1]
            results = fs.grep(pattern, path, ignore_case, recursive, line_numbers, count_only, invert)
            output = "\n".join(results)

        elif cmd_name == "echo":
            output = " ".join(args)

        elif cmd_name == "wc":
            if not args:
                return ShellResult({
                    "success": False, "stdout": "", "stderr": "",
                    "returncode": -1, "error": "Missing file path",
                })
            lines_mode = "-l" in args
            words_mode = "-w" in args
            chars_mode = "-c" in args or "-m" in args
            path = [a for a in args if not a.startswith("-")][0]
            content = fs.read_file(path)
            if content.startswith("Error:"):
                return ShellResult({
                    "success": False, "stdout": "", "stderr": "",
                    "returncode": -1, "error": content,
                })
            if lines_mode:
                output = str(len(content.splitlines()))
            elif words_mode:
                output = str(len(content.split()))
            elif chars_mode:
                output = str(len(content))
            else:
                # Default: lines, words, chars
                output = f"{len(content.splitlines())} {len(content.split())} {len(content)}"

        elif cmd_name == "sort":
            if not args:
                return ShellResult({
                    "success": False, "stdout": "", "stderr": "",
                    "returncode": -1, "error": "Missing file path",
                })
            reverse = "-r" in args
            path = [a for a in args if not a.startswith("-")][0]
            content = fs.read_file(path)
            if content.startswith("Error:"):
                return ShellResult({
                    "success": False, "stdout": "", "stderr": "",
                    "returncode": -1, "error": content,
                })
            lines = content.splitlines()
            sorted_lines = sorted(lines, reverse=reverse)
            output = "\n".join(sorted_lines)

        elif cmd_name == "uniq":
            if not args:
                return ShellResult({
                    "success": False, "stdout": "", "stderr": "",
                    "returncode": -1, "error": "Missing file path",
                })
            path = [a for a in args if not a.startswith("-")][0]
            content = fs.read_file(path)
            if content.startswith("Error:"):
                return ShellResult({
                    "success": False, "stdout": "", "stderr": "",
                    "returncode": -1, "error": content,
                })
            lines = content.splitlines()
            unique_lines = []
            prev = None
            for line in lines:
                if line != prev:
                    unique_lines.append(line)
                    prev = line
            output = "\n".join(unique_lines)

        elif cmd_name == "tree":
            path = args[0] if args and not args[0].startswith("-") else "."
            # Simple tree implementation
            from pathlib import Path
            p = Path(path)
            if not p.exists():
                return ShellResult({
                    "success": False, "stdout": "", "stderr": "",
                    "returncode": -1, "error": f"{path} does not exist",
                })
            lines = []
            for item in sorted(p.rglob('*')):
                rel = item.relative_to(p)
                depth = len(rel.parts) - 1
                indent = "  " * depth
                name = rel.name
                if item.is_dir():
                    lines.append(f"{indent}{name}/")
                else:
                    lines.append(f"{indent}{name}")
            output = "\n".join(lines) if lines else "(empty)"

        elif cmd_name == "env":
            # Show environment variables
            import os
            output = "\n".join(f"{k}={v}" for k, v in sorted(os.environ.items()))

        elif cmd_name == "search":
            # Web search using DuckDuckGo
            if not args:
                return ShellResult({
                    "success": False, "stdout": "", "stderr": "",
                    "returncode": -1, "error": "Missing search query",
                })
            query = " ".join(args)
            output = fs.search(query)

        else:
            return ShellResult({
                "success": False,
                "stdout": "",
                "stderr": "",
                "returncode": -1,
                "error": f"Command '{cmd_name}' not supported. Available: ls, cat, head, tail, cp, mv, rm, mkdir, touch, find, grep, pwd, which, search",
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