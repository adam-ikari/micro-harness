# src/micro_harness/mcp/__init__.py
"""MCP module for zero-agent."""

from micro_harness.mcp.types import Tool, ToolCall, ToolResult
from micro_harness.mcp.client import MCPClient

__all__ = ["Tool", "ToolCall", "ToolResult", "MCPClient"]
