# src/micro_harness/mcp/types.py
"""MCP type definitions."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Tool:
    """MCP 工具定义。"""
    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolCall:
    """工具调用请求。"""
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolResult:
    """工具执行结果。"""
    content: str
    is_error: bool = False
