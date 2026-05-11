# tests/test_errors.py
"""Tests for error handling."""

import pytest

from spark.errors import (
    SparkError,
    LLMError,
    LLMConnectionError,
    LLMResponseError,
    LLMTimeoutError,
    ToolError,
    ToolNotFoundError,
    ToolExecutionError,
    SecurityError,
    PathNotTrustedError,
    CommandBlockedError,
    PermissionDeniedError,
    ConfigError,
    ConfigNotFoundError,
    ConfigValidationError,
    format_error,
)


class TestErrorHierarchy:
    """Tests for error class hierarchy."""

    def test_spark_error_is_base(self):
        """Test SparkError is base for all errors."""
        assert issubclass(LLMError, SparkError)
        assert issubclass(ToolError, SparkError)
        assert issubclass(SecurityError, SparkError)
        assert issubclass(ConfigError, SparkError)

    def test_llm_errors_hierarchy(self):
        """Test LLM error hierarchy."""
        assert issubclass(LLMConnectionError, LLMError)
        assert issubclass(LLMResponseError, LLMError)
        assert issubclass(LLMTimeoutError, LLMError)

    def test_tool_errors_hierarchy(self):
        """Test tool error hierarchy."""
        assert issubclass(ToolNotFoundError, ToolError)
        assert issubclass(ToolExecutionError, ToolError)

    def test_security_errors_hierarchy(self):
        """Test security error hierarchy."""
        assert issubclass(PathNotTrustedError, SecurityError)
        assert issubclass(CommandBlockedError, SecurityError)
        assert issubclass(PermissionDeniedError, SecurityError)

    def test_config_errors_hierarchy(self):
        """Test config error hierarchy."""
        assert issubclass(ConfigNotFoundError, ConfigError)
        assert issubclass(ConfigValidationError, ConfigError)


class TestErrorMessages:
    """Tests for error messages."""

    def test_spark_error_message(self):
        """Test SparkError message."""
        error = SparkError("Something went wrong")
        assert str(error) == "Something went wrong"

    def test_spark_error_with_details(self):
        """Test SparkError with details."""
        error = SparkError("Error occurred", {"key": "value"})
        assert "Error occurred" in str(error)
        assert "key" in str(error)
        assert "value" in str(error)

    def test_llm_connection_error(self):
        """Test LLMConnectionError."""
        error = LLMConnectionError("Cannot connect", {"url": "http://localhost:11434"})
        assert "Cannot connect" in str(error)
        assert error.details["url"] == "http://localhost:11434"

    def test_tool_not_found_error(self):
        """Test ToolNotFoundError."""
        error = ToolNotFoundError("Tool not found", {"tool": "Bash"})
        assert "Tool not found" in str(error)
        assert error.details["tool"] == "Bash"

    def test_path_not_trusted_error(self):
        """Test PathNotTrustedError."""
        error = PathNotTrustedError(
            "Path not trusted",
            {"path": "/etc/passwd", "operation": "write"}
        )
        assert "Path not trusted" in str(error)
        assert error.details["path"] == "/etc/passwd"
        assert error.details["operation"] == "write"


class TestFormatError:
    """Tests for format_error function."""

    def test_format_llm_connection_error_en(self):
        """Test formatting LLMConnectionError in English."""
        error = LLMConnectionError("Cannot connect")
        msg = format_error(error, "en")
        assert "connect" in msg.lower() or "ollama" in msg.lower()

    def test_format_llm_connection_error_zh(self):
        """Test formatting LLMConnectionError in Chinese."""
        error = LLMConnectionError("Cannot connect")
        msg = format_error(error, "zh")
        assert "连接" in msg or "LLM" in msg

    def test_format_llm_connection_error_ja(self):
        """Test formatting LLMConnectionError in Japanese."""
        error = LLMConnectionError("Cannot connect")
        msg = format_error(error, "ja")
        assert "接続" in msg or "LLM" in msg

    def test_format_tool_not_found_error(self):
        """Test formatting ToolNotFoundError."""
        error = ToolNotFoundError("Not found", {"tool": "Bash"})
        msg = format_error(error, "en")
        assert "Bash" in msg

    def test_format_path_not_trusted_error(self):
        """Test formatting PathNotTrustedError."""
        error = PathNotTrustedError("Not trusted", {"path": "/tmp", "operation": "write"})
        msg = format_error(error, "en")
        assert "/tmp" in msg
        assert "write" in msg

    def test_format_command_blocked_error(self):
        """Test formatting CommandBlockedError."""
        error = CommandBlockedError("Blocked", {"command": "rm -rf /"})
        msg = format_error(error, "en")
        assert "rm -rf /" in msg

    def test_format_generic_error(self):
        """Test formatting generic exception."""
        error = ValueError("Something went wrong")
        msg = format_error(error, "en")
        assert "Error" in msg
        assert "Something went wrong" in msg

    def test_format_unknown_language_defaults_to_en(self):
        """Test unknown language defaults to English."""
        error = LLMConnectionError("Cannot connect")
        msg = format_error(error, "unknown")
        assert "connect" in msg.lower() or "ollama" in msg.lower()
