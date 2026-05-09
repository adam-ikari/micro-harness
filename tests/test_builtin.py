# tests/test_builtin.py
"""Tests for cross-platform shell execution."""
import pytest
from spark.builtin.shell import execute, get_tool_definition


def test_get_tool_definition():
    """Test tool definition."""
    tool_def = get_tool_definition()

    assert tool_def["name"] == "run_shell"
    assert "description" in tool_def
    assert "parameters" in tool_def


def test_shell_execute_pwd():
    """Test pwd command (pure Python)."""
    result = execute("pwd")

    assert result["success"] is True
    assert "/" in result["stdout"] or "\\" in result["stdout"]


def test_shell_execute_ls():
    """Test ls command (pure Python)."""
    result = execute("ls .")

    assert result["success"] is True
    # Should list current directory


def test_shell_execute_cat():
    """Test cat command (pure Python)."""
    result = execute("cat pyproject.toml")

    assert result["success"] is True
    assert "spark" in result["stdout"]


def test_shell_execute_failed():
    """Test non-existent file."""
    result = execute("cat /nonexistent_file_12345.txt")

    assert result["success"] is False
    assert result["error"] != "" or result["stderr"] != ""


def test_shell_execute_empty():
    """Test empty command."""
    result = execute("")

    assert result["success"] is False
    assert "empty" in result["error"].lower()


def test_shell_execute_which():
    """Test which command (pure Python)."""
    result = execute("which python")

    assert result["success"] is True
    assert "python" in result["stdout"].lower()
