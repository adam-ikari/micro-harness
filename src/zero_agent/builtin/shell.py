# src/zero_agent/builtin/shell.py
"""Shell execution tool with security validation."""

import subprocess
import shlex
import logging
from typing import Any, Optional

from zero_agent.security.command import CommandParser, RiskLevel

logger = logging.getLogger(__name__)

# Security limits
MAX_COMMAND_LENGTH = 4096
MIN_TIMEOUT = 1
MAX_TIMEOUT = 300
DEFAULT_TIMEOUT = 30


class ShellResult(dict):
    """Typed result for shell execution."""

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
        "description": "Execute shell command. Use for file operations, network requests, and any system tasks.",
        "parameters": {
            "command": {
                "type": "string",
                "description": "Shell command to execute",
            },
            "timeout": {
                "type": "integer",
                "description": f"Timeout in seconds (default {DEFAULT_TIMEOUT}, max {MAX_TIMEOUT})",
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


def validate_timeout(timeout: int) -> int:
    """Validate and clamp timeout value.

    Args:
        timeout: Requested timeout

    Returns:
        int: Valid timeout within bounds
    """
    if timeout < MIN_TIMEOUT:
        return MIN_TIMEOUT
    if timeout > MAX_TIMEOUT:
        return MAX_TIMEOUT
    return timeout


def execute(command: str, timeout: int = DEFAULT_TIMEOUT) -> ShellResult:
    """Execute shell command with security validation.

    Args:
        command: Command to execute
        timeout: Timeout in seconds (clamped to 1-300)

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

    # Validate timeout
    timeout = validate_timeout(timeout)

    # Parse command for logging (not for execution)
    parser = CommandParser()
    cmd_name, args, meta = parser.parse(command)
    risk = parser.get_risk_level(command)

    logger.info(f"Executing command: {cmd_name} (risk: {risk.value})")

    try:
        # Execute with shell=True for complex commands (pipes, redirects)
        # Security is handled by:
        # 1. Command validation above
        # 2. Path trust system in agent
        # 3. Risk level assessment
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        return ShellResult({
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "error": None if result.returncode == 0 else result.stderr,
        })

    except subprocess.TimeoutExpired:
        return ShellResult({
            "success": False,
            "stdout": "",
            "stderr": "",
            "returncode": -1,
            "error": f"Command timed out after {timeout} seconds",
        })

    except Exception as e:
        logger.exception(f"Command execution failed: {e}")
        return ShellResult({
            "success": False,
            "stdout": "",
            "stderr": "",
            "returncode": -1,
            "error": str(e),
        })
