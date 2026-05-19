# tests/test_mcp.py
import pytest
from spark.mcp.types import Tool, ToolCall, ToolResult
from spark.mcp.client import MCPClient


def test_mcp_types_tool():
    """测试 Tool 类型"""
    tool = Tool(
        name="test_tool",
        description="A test tool",
        input_schema={"type": "object"},
    )

    assert tool.name == "test_tool"
    assert tool.description == "A test tool"


def test_mcp_types_tool_call():
    """测试 ToolCall 类型"""
    call = ToolCall(
        name="test_tool",
        arguments={"arg1": "value1"},
    )

    assert call.name == "test_tool"
    assert call.arguments["arg1"] == "value1"


def test_mcp_types_tool_result():
    """测试 ToolResult 类型"""
    result = ToolResult(
        content="Result content",
        is_error=False,
    )

    assert result.content == "Result content"
    assert result.is_error is False


def test_mcp_client_init():
    """测试 MCP 客户端初始化"""
    client = MCPClient({})

    assert client.servers_config == {}
    assert client.tools == []


def test_mcp_client_get_tool_definitions():
    """测试获取工具定义"""
    client = MCPClient({})

    # 添加模拟工具
    from spark.mcp.types import Tool
    client.tools = [
        Tool(name="tool1", description="Tool 1", input_schema={}),
        Tool(name="tool2", description="Tool 2", input_schema={}),
    ]

    definitions = client.get_tool_definitions()

    assert len(definitions) == 2
    assert definitions[0]["name"] == "tool1"
