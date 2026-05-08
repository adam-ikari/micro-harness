# src/zero_agent/builtin/shell.py
"""Shell execution tool."""

import subprocess
from typing import Any


def get_tool_definition() -> dict[str, Any]:
    """Get tool definition for LLM.

    Returns:
        dict: Tool definition with name, description, parameters
    """
    return {
        "name": "run_shell",
        "description": "Execute shell command. Use for file operations, network requests, and any system tasks.",
        "parameters": {
            "command": {
                "type": "string",
                "description": "Shell command to execute",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default 30)",
            },
        },
    }


def execute(command: str, timeout: int = 30) -> dict[str, Any]:
    """Execute shell command.

    Args:
        command: Command to execute
        timeout: Timeout in seconds

    Returns:
        dict: Result with success, stdout, stderr, error
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "error": None if result.returncode == 0 else result.stderr,
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "returncode": -1,
            "error": f"Command timed out after {timeout} seconds",
        }

    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "returncode": -1,
            "error": str(e),
        }
