# src/zero_agent/mcp/client.py
"""MCP client for connecting to external MCP servers."""

import asyncio
import shutil
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from zero_agent.mcp.types import Tool, ToolCall, ToolResult


class MCPClient:
    """MCP 客户端，管理多个 MCP server 连接。"""

    def __init__(self, servers_config: dict[str, Any]):
        self.servers_config = servers_config
        self.sessions: dict[str, ClientSession] = {}
        self.tools: list[Tool] = []
        self._connected = False

    def connect_all(self) -> None:
        """同步连接所有配置的 MCP server。"""
        if self._connected:
            return
        try:
            asyncio.run(self._connect_all_async())
            self._connected = True
        except Exception as e:
            print(f"MCP connection error: {e}")

    async def _connect_all_async(self) -> None:
        """异步连接所有 MCP server。"""
        for name, config in self.servers_config.items():
            try:
                await self._connect_server(name, config)
            except Exception as e:
                print(f"Failed to connect to MCP server {name}: {e}")

    async def _connect_server(self, name: str, config: dict) -> None:
        """连接单个 MCP server。"""
        command = config.get("command")
        args = config.get("args", [])

        # Check if command exists
        if not shutil.which(command):
            raise ValueError(f"Command not found: {command}")

        server_params = StdioServerParameters(
            command=command,
            args=args,
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                self.sessions[name] = session

                # Get tool list
                tools_result = await session.list_tools()
                for tool in tools_result.tools:
                    self.tools.append(Tool(
                        name=tool.name,
                        description=tool.description or "",
                        input_schema=tool.inputSchema or {},
                    ))

    def call_tool_sync(self, call: ToolCall) -> ToolResult:
        """同步调用工具。"""
        try:
            return asyncio.run(self._call_tool_async(call))
        except Exception as e:
            return ToolResult(content=f"Error: {e}", is_error=True)

    async def _call_tool_async(self, call: ToolCall) -> ToolResult:
        """调用工具。

        Args:
            call: 工具调用请求

        Returns:
            ToolResult: 执行结果
        """
        # Find the server that has this tool
        for name, session in self.sessions.items():
            try:
                result = await session.call_tool(call.name, call.arguments)
                return ToolResult(
                    content=str(result.content),
                    is_error=result.isError if hasattr(result, "isError") else False,
                )
            except Exception:
                continue

        return ToolResult(
            content=f"Tool {call.name} not found",
            is_error=True,
        )

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """获取所有工具定义（供 LLM 使用）。"""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.input_schema.get("properties", {}),
            }
            for tool in self.tools
        ]

    def has_tools(self) -> bool:
        """检查是否有可用工具。"""
        return len(self.tools) > 0
