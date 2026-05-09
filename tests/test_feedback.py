# tests/test_feedback.py
"""Tests for hallucination prevention in small models."""
import pytest
from micro_harness.feedback import (
    ToolResultVerifier,
    HallucinationPreventer,
    VerifiedResult,
    ResultStatus,
)


def test_verifier_success():
    """Test verifying successful tool result."""
    verifier = ToolResultVerifier()
    result = {
        "success": True,
        "stdout": "file contents",
        "stderr": "",
        "returncode": 0,
    }
    verified = verifier.verify("run_shell", result)
    assert verified.status == ResultStatus.SUCCESS
    assert verified.tool_name == "run_shell"
    assert verified.error is None


def test_verifier_failure():
    """Test verifying failed tool result."""
    verifier = ToolResultVerifier()
    result = {
        "success": False,
        "stdout": "",
        "stderr": "Permission denied",
        "returncode": 1,
        "error": "Permission denied",
    }
    verified = verifier.verify("run_shell", result)
    assert verified.status == ResultStatus.FAILURE
    assert verified.error == "Permission denied"


def test_verifier_denied():
    """Test creating denied result."""
    verifier = ToolResultVerifier()
    verified = verifier.verify_denied("run_shell", "Write blocked in plan mode")
    assert verified.status == ResultStatus.DENIED
    assert "blocked" in verified.error.lower()


def test_hallucination_preventer_format_success():
    """Test formatting success result."""
    hp = HallucinationPreventer()
    result = {
        "success": True,
        "stdout": "output",
        "stderr": "",
        "returncode": 0,
    }
    formatted = hp.format_result("run_shell", result)
    assert "SUCCESS" in formatted
    assert "✓" in formatted
    assert "[TOOL RESULT:" in formatted


def test_hallucination_preventer_format_failure():
    """Test formatting failure result with anti-hallucination markers."""
    hp = HallucinationPreventer()
    result = {
        "success": False,
        "stdout": "",
        "stderr": "Error",
        "returncode": 1,
        "error": "Command failed",
    }
    formatted = hp.format_result("run_shell", result)
    assert "FAILURE" in formatted
    assert "✗" in formatted
    assert "IMPORTANT" in formatted
    assert "do not proceed" in formatted.lower()


def test_hallucination_preventer_format_denied():
    """Test formatting denied result."""
    hp = HallucinationPreventer()
    formatted = hp.format_denied("run_shell", "Permission denied")
    assert "DENIED" in formatted
    assert "✗" in formatted


def test_model_acknowledgment_check():
    """Test checking if model acknowledged failure."""
    hp = HallucinationPreventer()
    verified_result = VerifiedResult(
        status=ResultStatus.FAILURE,
        tool_name="run_shell",
        output="",
        error="Permission denied",
    )

    # Model that acknowledges failure
    acknowledged, _ = hp.check_model_response(
        "The command failed due to permission denied",
        verified_result
    )
    assert acknowledged is True

    # Model that ignores failure (hallucinates success)
    acknowledged, hint = hp.check_model_response(
        "I have successfully completed the task",
        verified_result
    )
    assert acknowledged is False
    assert "REMINDER" in hint


def test_failure_pattern_detection():
    """Test that we trust explicit flags, not output patterns.

    This is a design decision: pattern detection causes false positives
    (e.g., grep "error:" returns "error:" in output but is successful).
    We trust explicit success/returncode flags instead.
    """
    verifier = ToolResultVerifier()

    # Output with "error:" but success=True - should be SUCCESS
    # (e.g., grep "error:" file.txt returns lines with "error:")
    result = {
        "success": True,
        "stdout": "error: file not found",  # This could be grep output
        "stderr": "",
        "returncode": 0,
    }
    verified = verifier.verify("run_shell", result)
    # Should trust explicit flags, not infer from output
    assert verified.status == ResultStatus.SUCCESS

    # Actual failure case - explicit success=False
    result = {
        "success": False,
        "stdout": "",
        "stderr": "error: file not found",
        "returncode": 1,
        "error": "Command failed",
    }
    verified = verifier.verify("run_shell", result)
    assert verified.status == ResultStatus.FAILURE


def test_output_truncation():
    """Test that long output is truncated for small models."""
    hp = HallucinationPreventer()
    long_output = "x" * 2000
    result = {
        "success": True,
        "stdout": long_output,
        "stderr": "",
        "returncode": 0,
    }
    formatted = hp.format_result("run_shell", result)
    # Should be truncated
    assert len(formatted) < len(long_output) + 200
    assert "truncated" in formatted.lower()
