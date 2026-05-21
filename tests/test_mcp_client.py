# tests/test_mcp_client.py
"""Tests for MCP client."""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import asyncio

from spark.mcp.client import MCPClient
from spark.mcp.types import Tool, ToolCall, ToolResult


class TestMCPClientInit:
    """Tests for MCPClient initialization."""

    def test_init_empty(self):
        """Test initialization with empty config."""
        client = MCPClient({})
        assert client.servers_config == {}
        assert client.tools == []
        assert not client.is_connected()

    def test_init_with_config(self):
        """Test initialization with server config."""
        config = {
            "server1": {"command": "test-cmd", "args": []}
        }
        client = MCPClient(config)
        assert client.servers_config == config
        assert not client.is_connected()

    def test_is_connecting_false_initially(self):
        """Test is_connecting returns False initially."""
        client = MCPClient({})
        assert not client.is_connecting()


class TestMCPClientTools:
    """Tests for tool management."""

    def test_has_tools_false_initially(self):
        """Test has_tools returns False initially."""
        client = MCPClient({})
        assert not client.has_tools()

    def test_get_tool_definitions_empty(self):
        """Test get_tool_definitions returns empty list."""
        client = MCPClient({})
        definitions = client.get_tool_definitions()
        assert definitions == []

    def test_get_tool_definitions_with_tools(self):
        """Test get_tool_definitions with tools."""
        client = MCPClient({})
        client.tools = [
            Tool(name="test_tool", description="Test", input_schema={"properties": {"path": {"type": "string"}}})
        ]
        definitions = client.get_tool_definitions()
        assert len(definitions) == 1
        assert definitions[0]["name"] == "test_tool"


class TestMCPClientConnection:
    """Tests for connection management."""

    def test_connect_all_async_no_servers(self):
        """Test connect_all_async with no servers."""
        client = MCPClient({})
        client.connect_all_async()
        # Should not block or error
        assert not client.is_connected()

    def test_connect_all_no_servers(self):
        """Test connect_all with no servers."""
        client = MCPClient({})
        client.connect_all()
        # With no servers, it sets connected=True but has no tools
        assert not client.has_tools()


class TestMCPClientToolCalls:
    """Tests for tool calling."""

    def test_call_tool_sync_no_tools(self):
        """Test call_tool_sync with no tools."""
        client = MCPClient({})
        call = ToolCall(name="test", arguments={})
        result = client.call_tool_sync(call)
        assert result.is_error is True
        assert "not found" in result.content

    @patch('spark.mcp.client.asyncio.run')
    def test_call_tool_sync_with_error(self, mock_run):
        """Test call_tool_sync handles errors."""
        mock_run.side_effect = Exception("Test error")
        client = MCPClient({})
        call = ToolCall(name="test", arguments={})
        result = client.call_tool_sync(call)
        assert result.is_error is True
        assert "Error" in result.content


class TestMCPClientCleanup:
    """Tests for cleanup."""

    def test_cleanup_no_loop(self):
        """Test cleanup with no event loop."""
        client = MCPClient({})
        client.cleanup()
        # Should not error

    def test_cleanup_with_loop(self):
        """Test cleanup with event loop."""
        client = MCPClient({})
        client._loop = MagicMock()
        client.cleanup()
        # Should call loop.close()


class TestToolTypes:
    """Tests for MCP types."""

    def test_tool_creation(self):
        """Test Tool creation."""
        tool = Tool(name="test", description="Test tool", input_schema={})
        assert tool.name == "test"
        assert tool.description == "Test tool"

    def test_tool_call_creation(self):
        """Test ToolCall creation."""
        call = ToolCall(name="test", arguments={"path": "/tmp"})
        assert call.name == "test"
        assert call.arguments["path"] == "/tmp"

    def test_tool_result_creation(self):
        """Test ToolResult creation."""
        result = ToolResult(content="output", is_error=False)
        assert result.content == "output"
        assert result.is_error is False

    def test_tool_result_error(self):
        """Test ToolResult error."""
        result = ToolResult(content="error message", is_error=True)
        assert result.is_error is True