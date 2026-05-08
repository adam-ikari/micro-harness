# tests/test_builtin.py
import pytest
from zero_agent.builtin.shell import execute, get_tool_definition


def test_get_tool_definition():
    """测试获取工具定义"""
    tool_def = get_tool_definition()

    assert tool_def["name"] == "run_shell"
    assert "description" in tool_def
    assert "parameters" in tool_def


def test_shell_execute_simple():
    """测试执行简单命令"""
    result = execute("echo 'hello world'")

    assert result["success"] is True
    assert "hello world" in result["stdout"]


def test_shell_execute_with_timeout():
    """测试带超时执行"""
    result = execute("echo 'test'", timeout=5)

    assert result["success"] is True


def test_shell_execute_failed():
    """测试执行失败命令"""
    result = execute("ls /nonexistent_directory_12345")

    assert result["success"] is False
    assert result["stderr"] != ""


def test_shell_execute_timeout():
    """测试超时"""
    # 使用 sleep 命令测试超时
    result = execute("sleep 10", timeout=1)

    assert result["success"] is False
    assert "timed out" in result["error"].lower()
