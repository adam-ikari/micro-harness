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

# Try to import bashlex for better parsing
try:
    import bashlex
    HAS_BASHLEX = True
except ImportError:
    HAS_BASHLEX = False


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


def execute_pipeline(command: str) -> ShellResult:
    """Execute piped commands like "ls | grep .py | wc -l".

    Uses bashlex for proper shell parsing when available.

    Args:
        command: Pipeline command string

    Returns:
        ShellResult: Final result after all pipes
    """
    commands = []

    if HAS_BASHLEX:
        try:
            tree = bashlex.parse(command)
            for node in tree:
                if hasattr(node, 'kind') and node.kind == 'pipeline':
                    for part in node.parts:
                        if hasattr(part, 'kind') and part.kind == 'command':
                            words = []
                            for w in part.parts:
                                if hasattr(w, 'word'):
                                    words.append(w.word)
                            if words:
                                commands.append(words)
                elif hasattr(node, 'kind') and node.kind == 'command':
                    words = []
                    for w in node.parts:
                        if hasattr(w, 'word'):
                            words.append(w.word)
                    if words:
                        commands.append(words)
        except Exception:
            # Fall back to simple split
            import re
            parts = re.split(r'\s*\|\s*', command)
            commands = [p.strip().split() for p in parts if p.strip()]
    else:
        import re
        parts = re.split(r'\s*\|\s*', command)
        commands = [p.strip().split() for p in parts if p.strip()]

    if len(commands) < 2:
        return execute(command)  # No actual pipe

    # Execute each command, passing output to next
    current_input = None
    for cmd_parts in commands:
        if isinstance(cmd_parts, str):
            cmd_parts = cmd_parts.split()
        result = execute_single_with_args(cmd_parts[0], cmd_parts[1:], stdin_data=current_input)

        if not result["success"]:
            return result

        current_input = result["stdout"]

    # Return final result
    return ShellResult({
        "success": True,
        "stdout": current_input or "",
        "stderr": "",
        "returncode": 0,
    })


def execute_single_with_args(cmd_name: str, args: list, stdin_data: str = None) -> ShellResult:
    """Execute a single command with pre-parsed args.

    Args:
        cmd_name: Command name
        args: List of arguments
        stdin_data: Optional input data (from previous pipe)

    Returns:
        ShellResult: Command result
    """
    fs = FileSystemOperations()
    output = ""

    # Handle stdin for filter commands
    input_text = stdin_data or ""

    try:
        # Filter commands that work with stdin
        if cmd_name == "grep":
            # Pattern should be first non-flag argument
            pattern = [a for a in args if not a.startswith("-")][0] if args else ""
            invert = "-v" in args or "--invert-match" in args

            if input_text:
                lines = input_text.split("\n")
                matched = [l for l in lines if (pattern in l) != invert]
                output = "\n".join(matched)
            else:
                # Run grep on files
                result = fs.grep(pattern, ".", recursive="-r" in args)
                output = "\n".join(result) if result else ""

        elif cmd_name == "wc":
            lines_flag = "-l" in args
            words_flag = "-w" in args
            chars_flag = "-c" in args or "-m" in args

            if input_text:
                if lines_flag or not (words_flag or chars_flag):
                    output = str(len(input_text.split("\n")))
                elif words_flag:
                    output = str(len(input_text.split()))
                else:
                    output = str(len(input_text))
            else:
                output = "0"

        elif cmd_name == "sort":
            reverse = "-r" in args
            if input_text:
                lines = input_text.split("\n")
                lines.sort(reverse=reverse)
                output = "\n".join(lines)
            else:
                output = ""

        elif cmd_name == "uniq":
            if input_text:
                lines = input_text.split("\n")
                unique = []
                prev = None
                for line in lines:
                    if line != prev:
                        unique.append(line)
                        prev = line
                output = "\n".join(unique)
            else:
                output = ""

        elif cmd_name == "head":
            lines = 10
            if "-n" in args:
                idx = args.index("-n")
                if idx + 1 < len(args):
                    lines = int(args[idx + 1])
            if input_text:
                output = "\n".join(input_text.split("\n")[:lines])
            else:
                path = [a for a in args if not a.startswith("-")][0] if args else "."
                output = fs.read_file(path, lines=lines)

        elif cmd_name == "tail":
            lines = 10
            if "-n" in args:
                idx = args.index("-n")
                if idx + 1 < len(args):
                    lines = int(args[idx + 1])
            if input_text:
                output = "\n".join(input_text.split("\n")[-lines:])
            else:
                path = [a for a in args if not a.startswith("-")][0] if args else "."
                output = fs.read_file(path, lines=lines, tail=True)

        elif cmd_name == "ls":
            path = args[0] if args and not args[0].startswith("-") else "."
            all_files = "-a" in args or "--all" in args
            long_fmt = "-l" in args
            result = fs.list_dir(path, all_files, long_fmt)
            output = "\n".join(result)

        elif cmd_name == "cat":
            if args:
                output = fs.read_file(args[0])
            elif input_text:
                output = input_text
            else:
                output = ""

        elif cmd_name == "pwd":
            output = fs.pwd()

        elif cmd_name == "echo":
            output = " ".join(args)

        elif cmd_name == "find":
            path = args[0] if args and not args[0].startswith("-") else "."
            name = None
            file_type = None
            if "-name" in args:
                idx = args.index("-name")
                if idx + 1 < len(args):
                    name = args[idx + 1]
            if "-type" in args:
                idx = args.index("-type")
                if idx + 1 < len(args):
                    file_type = args[idx + 1]
            results = fs.find(path, name, file_type)
            output = "\n".join(results) if results else ""

        else:
            # Unknown command - return input unchanged
            output = input_text

        return ShellResult({
            "success": True,
            "stdout": output,
            "stderr": "",
            "returncode": 0,
        })

    except Exception as e:
        return ShellResult({
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "returncode": 1,
            "error": str(e),
        })


def execute_single(command: str, stdin_data: str = None) -> ShellResult:
    """Execute a single command, optionally with stdin input.

    Args:
        command: Single command to execute
        stdin_data: Optional input data (from previous pipe)

    Returns:
        ShellResult: Command result
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

    # Handle stdin for filter commands
    input_text = stdin_data or ""

    try:
        # Filter commands that work with stdin
        if cmd_name == "grep":
            # Pattern should be first non-flag argument
            pattern = [a for a in args if not a.startswith("-")][0] if args else ""
            invert = "-v" in args or "--invert-match" in args

            if input_text:
                lines = input_text.split("\n")
                matched = [l for l in lines if (pattern in l) != invert]
                output = "\n".join(matched)
            else:
                # Run grep on files
                result = fs.grep(pattern, ".", recursive="-r" in args)
                output = "\n".join(result) if result else ""

        elif cmd_name == "wc":
            lines_flag = "-l" in args
            words_flag = "-w" in args
            chars_flag = "-c" in args or "-m" in args

            if input_text:
                if lines_flag or not (words_flag or chars_flag):
                    output = str(len(input_text.split("\n")))
                elif words_flag:
                    output = str(len(input_text.split()))
                else:
                    output = str(len(input_text))
            else:
                output = "0"

        elif cmd_name == "sort":
            reverse = "-r" in args
            if input_text:
                lines = input_text.split("\n")
                lines.sort(reverse=reverse)
                output = "\n".join(lines)
            else:
                output = ""

        elif cmd_name == "uniq":
            if input_text:
                lines = input_text.split("\n")
                unique = []
                prev = None
                for line in lines:
                    if line != prev:
                        unique.append(line)
                        prev = line
                output = "\n".join(unique)
            else:
                output = ""

        elif cmd_name == "head":
            lines = 10
            if "-n" in args:
                idx = args.index("-n")
                if idx + 1 < len(args):
                    lines = int(args[idx + 1])
            if input_text:
                output = "\n".join(input_text.split("\n")[:lines])
            else:
                path = [a for a in args if not a.startswith("-")][0] if args else "."
                output = fs.read_file(path, lines=lines)

        elif cmd_name == "tail":
            lines = 10
            if "-n" in args:
                idx = args.index("-n")
                if idx + 1 < len(args):
                    lines = int(args[idx + 1])
            if input_text:
                output = "\n".join(input_text.split("\n")[-lines:])
            else:
                path = [a for a in args if not a.startswith("-")][0] if args else "."
                output = fs.read_file(path, lines=lines, tail=True)

        elif cmd_name == "sed":
            # Basic sed support for s/pattern/replacement/
            import re
            if args and args[0].startswith("s/"):
                parts = args[0][2:].rstrip("/").split("/")
                if len(parts) >= 2:
                    pattern, replacement = parts[0], parts[1]
                    flags = parts[2] if len(parts) > 2 else ""
                    regex_flags = re.IGNORECASE if "i" in flags else 0
                    output = re.sub(pattern, replacement, input_text, flags=regex_flags)
                else:
                    output = input_text
            else:
                output = input_text

        elif cmd_name == "awk":
            # Basic awk support for {print $N}
            import re
            if args and "print" in " ".join(args):
                # Extract field number
                match = re.search(r'\$([0-9]+)', " ".join(args))
                if match:
                    field_num = int(match.group(1)) - 1  # awk is 1-indexed
                    lines = input_text.split("\n") if input_text else []
                    result_lines = []
                    for line in lines:
                        fields = line.split()
                        if field_num < len(fields):
                            result_lines.append(fields[field_num])
                    output = "\n".join(result_lines)
                else:
                    output = input_text
            else:
                output = input_text

        elif cmd_name == "cut":
            # Basic cut support for -d and -f
            delimiter = " "
            fields = None
            if "-d" in args:
                idx = args.index("-d")
                if idx + 1 < len(args):
                    delimiter = args[idx + 1]
            if "-f" in args:
                idx = args.index("-f")
                if idx + 1 < len(args):
                    fields = args[idx + 1]

            if input_text and fields:
                lines = input_text.split("\n")
                result_lines = []
                for line in lines:
                    parts = line.split(delimiter)
                    # Handle field ranges like "1-3" or "2"
                    if "-" in fields:
                        start, end = map(int, fields.split("-"))
                        result_lines.append(delimiter.join(parts[start-1:end]))
                    else:
                        field_num = int(fields) - 1
                        if field_num < len(parts):
                            result_lines.append(parts[field_num])
                output = "\n".join(result_lines)
            else:
                output = input_text

        elif cmd_name == "tr":
            # Basic tr support
            if len(args) >= 2:
                from_set, to_set = args[0], args[1]
                if input_text:
                    trans = str.maketrans(from_set, to_set)
                    output = input_text.translate(trans)
                else:
                    output = ""
            else:
                output = input_text

        else:
            # Fall back to regular execute for non-filter commands
            return execute(command)

        return ShellResult({
            "success": True,
            "stdout": output,
            "stderr": "",
            "returncode": 0,
        })

    except Exception as e:
        return ShellResult({
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "returncode": 1,
            "error": str(e),
        })


def execute(command: str) -> ShellResult:
    """Execute command using Python implementation.

    All operations use Python's pathlib, shutil, and os modules.
    No shell dependency - consistent behavior across platforms.

    Supports pipes: "ls | grep .py" will chain commands.

    Args:
        command: Command to execute

    Returns:
        ShellResult: Result with success, stdout, stderr, returncode, error
    """
    # Check for pipes
    if "|" in command:
        return execute_pipeline(command)

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