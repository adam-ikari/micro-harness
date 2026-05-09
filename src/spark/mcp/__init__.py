# src/spark/mcp/__init__.py
"""MCP module for spark."""

from spark.mcp.types import Tool, ToolCall, ToolResult
from spark.mcp.client import MCPClient

__all__ = ["Tool", "ToolCall", "ToolResult", "MCPClient"]
