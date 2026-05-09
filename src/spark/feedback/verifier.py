# src/spark/feedback/verifier.py
"""Tool result verification to prevent hallucination in small models.

Small models (gemma3:4b, qwen2.5:3b) often hallucinate success when tools fail.
This module provides structured feedback to force models to acknowledge results.

First principles:
- Trust explicit flags (success, returncode) - most reliable signal
- Don't infer from output patterns - causes false positives
- Keep it simple - small models need clear, unambiguous signals
"""

from dataclasses import dataclass
from typing import Any, Optional
from enum import Enum


class ResultStatus(Enum):
    """Tool execution status."""
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    ERROR = "ERROR"
    DENIED = "DENIED"


@dataclass
class VerifiedResult:
    """Verified tool result with explicit status."""
    status: ResultStatus
    tool_name: str
    output: str
    error: Optional[str] = None
    requires_acknowledgment: bool = True

    def to_prompt(self) -> str:
        """Format as explicit prompt for small models.

        Critical: Use structured format that small models can't ignore.
        """
        if self.status == ResultStatus.SUCCESS:
            return (
                f"[TOOL RESULT: {self.tool_name}]\n"
                f"STATUS: SUCCESS ✓\n"
                f"OUTPUT:\n{self._truncate(self.output)}\n"
                f"[END RESULT]"
            )
        elif self.status == ResultStatus.FAILURE:
            return (
                f"[TOOL RESULT: {self.tool_name}]\n"
                f"STATUS: FAILURE ✗\n"
                f"ERROR: {self.error}\n"
                f"OUTPUT:\n{self._truncate(self.output)}\n"
                f"[ACTION REQUIRED: Acknowledge failure, do not proceed as if successful]\n"
                f"[END RESULT]"
            )
        elif self.status == ResultStatus.ERROR:
            return (
                f"[TOOL RESULT: {self.tool_name}]\n"
                f"STATUS: ERROR ✗\n"
                f"ERROR: {self.error}\n"
                f"[ACTION REQUIRED: Fix the error or report failure]\n"
                f"[END RESULT]"
            )
        else:  # DENIED
            return (
                f"[TOOL RESULT: {self.tool_name}]\n"
                f"STATUS: DENIED ✗\n"
                f"REASON: {self.error}\n"
                f"[ACTION REQUIRED: Request permission or try alternative]\n"
                f"[END RESULT]"
            )

    def _truncate(self, text: str, max_len: int = 1000) -> str:
        """Truncate output for small models."""
        if len(text) > max_len:
            return text[:max_len] + f"\n... [truncated, {len(text)} total chars]"
        return text


class ToolResultVerifier:
    """Verify tool results and format for small models.

    First principles:
    - Trust explicit flags (success, returncode) - most reliable
    - Don't infer from output patterns - causes false positives
    - Keep it simple - small models need clear signals
    """

    def verify(self, tool_name: str, result: dict[str, Any]) -> VerifiedResult:
        """Verify tool execution result.

        Args:
            tool_name: Name of the tool that was executed
            result: Raw result dict with success, stdout, stderr, error, returncode

        Returns:
            VerifiedResult: Verified result with explicit status
        """
        # Check explicit success flag first (most reliable)
        if result.get("success") is False:
            return VerifiedResult(
                status=ResultStatus.FAILURE,
                tool_name=tool_name,
                output=result.get("stdout", ""),
                error=result.get("error") or result.get("stderr") or "Unknown error",
            )

        # Check return code (second most reliable)
        returncode = result.get("returncode", 0)
        if returncode != 0:
            return VerifiedResult(
                status=ResultStatus.FAILURE,
                tool_name=tool_name,
                output=result.get("stdout", ""),
                error=result.get("stderr") or f"Exit code: {returncode}",
            )

        # Success case - trust explicit flags, don't second-guess with patterns
        # Pattern detection causes false positives (e.g., grep "error:" returns "error:" in output)
        output = result.get("stdout", "") or ""

        return VerifiedResult(
            status=ResultStatus.SUCCESS,
            tool_name=tool_name,
            output=output,
            error=None,
        )

    def verify_denied(self, tool_name: str, reason: str) -> VerifiedResult:
        """Create a denied result.

        Args:
            tool_name: Tool that was denied
            reason: Reason for denial

        Returns:
            VerifiedResult with DENIED status
        """
        return VerifiedResult(
            status=ResultStatus.DENIED,
            tool_name=tool_name,
            output="",
            error=reason,
        )

    def verify_error(self, tool_name: str, error: str) -> VerifiedResult:
        """Create an error result.

        Args:
            tool_name: Tool that errored
            error: Error message

        Returns:
            VerifiedResult with ERROR status
        """
        return VerifiedResult(
            status=ResultStatus.ERROR,
            tool_name=tool_name,
            output="",
            error=error,
        )


class HallucinationPreventer:
    """Prevent small models from hallucinating tool success.

    Key strategies:
    1. Structured output format with explicit STATUS markers
    2. Failure patterns that models can't ignore
    3. Action required prompts for failures
    4. Token-efficient formatting
    """

    # Prompt suffixes to add based on result status
    PROMPT_SUFFIXES = {
        ResultStatus.SUCCESS: "",
        ResultStatus.FAILURE: "\n\n[IMPORTANT: The tool FAILED. Do NOT proceed as if it succeeded. Acknowledge the failure.]",
        ResultStatus.ERROR: "\n\n[IMPORTANT: An ERROR occurred. Report the error to the user.]",
        ResultStatus.DENIED: "\n\n[IMPORTANT: Access DENIED. Do NOT proceed with this action.]",
    }

    def __init__(self, verifier: Optional[ToolResultVerifier] = None):
        """Initialize preventer.

        Args:
            verifier: Tool result verifier (creates default if None)
        """
        self.verifier = verifier or ToolResultVerifier()

    def format_result(self, tool_name: str, result: dict[str, Any]) -> str:
        """Format tool result with hallucination prevention.

        Args:
            tool_name: Name of executed tool
            result: Raw tool result

        Returns:
            str: Formatted result that prevents hallucination
        """
        verified = self.verifier.verify(tool_name, result)
        base_prompt = verified.to_prompt()
        suffix = self.PROMPT_SUFFIXES.get(verified.status, "")
        return base_prompt + suffix

    def format_denied(self, tool_name: str, reason: str) -> str:
        """Format denied tool call.

        Args:
            tool_name: Tool that was denied
            reason: Reason for denial

        Returns:
            str: Formatted denial message
        """
        verified = self.verifier.verify_denied(tool_name, reason)
        return verified.to_prompt()

    def format_error(self, tool_name: str, error: str) -> str:
        """Format tool error.

        Args:
            tool_name: Tool that errored
            error: Error message

        Returns:
            str: Formatted error message
        """
        verified = self.verifier.verify_error(tool_name, error)
        return verified.to_prompt()

    def check_model_response(self, response: str, last_result: VerifiedResult) -> tuple[bool, str]:
        """Check if model acknowledged the result correctly.

        Args:
            response: Model's response after tool result
            last_result: The verified result that was shown to model

        Returns:
            tuple: (acknowledged_correctly, hint_message)
        """
        if last_result.status == ResultStatus.SUCCESS:
            return True, ""

        # Check if model acknowledged failure
        response_lower = response.lower()
        acknowledged = any(
            word in response_lower
            for word in ["failed", "error", "couldn't", "could not", "didn't work", "unsuccessful", "denied"]
        )

        if acknowledged:
            return True, ""

        # Model didn't acknowledge failure - provide hint
        return False, (
            f"[REMINDER: The previous tool call ({last_result.tool_name}) "
            f"resulted in {last_result.status.value}. "
            f"Please acknowledge this in your response.]"
        )
