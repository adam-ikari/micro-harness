# src/zero_agent/mcp/client.py
"""MCP client for connecting to external MCP servers."""

import asyncio
import shutil
import threading
import logging
from typing import Any
from concurrent.futures import Future

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from zero_agent.mcp.types import Tool, ToolCall, ToolResult

logger = logging.getLogger(__name__)


class MCPClient:
    """MCP client managing multiple MCP server connections.

    Thread-safe implementation with proper locking for shared state.
    """

    def __init__(self, servers_config: dict[str, Any]):
        self.servers_config = servers_config
        self.sessions: dict[str, ClientSession] = {}
        self.tools: list[Tool] = []
        self._connected = False
        self._connecting = False
        self._connection_thread: threading.Thread | None = None
        self._lock = threading.RLock()  # Protect shared state
        self._loop: asyncio.AbstractEventLoop | None = None

    def connect_all_async(self) -> None:
        """Start async connection in background thread (non-blocking)."""
        with self._lock:
            if self._connected or self._connecting:
                return

            if not self.servers_config:
                return

            self._connecting = True

        self._connection_thread = threading.Thread(
            target=self._connect_in_thread,
            daemon=True
        )
        self._connection_thread.start()

    def _connect_in_thread(self) -> None:
        """Connect in background thread."""
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._connect_all_async())
            with self._lock:
                self._connected = True
        except Exception as e:
            logger.error(f"MCP connection error: {e}")
        finally:
            with self._lock:
                self._connecting = False

    def connect_all(self) -> None:
        """Synchronous connection (blocking)."""
        with self._lock:
            if self._connected:
                return
        try:
            asyncio.run(self._connect_all_async())
            with self._lock:
                self._connected = True
        except Exception as e:
            logger.error(f"MCP connection error: {e}")

    async def _connect_all_async(self) -> None:
        """Async connect all MCP servers."""
        for name, config in self.servers_config.items():
            try:
                await self._connect_server(name, config)
            except Exception as e:
                logger.error(f"Failed to connect to MCP server {name}: {e}")

    async def _connect_server(self, name: str, config: dict) -> None:
        """Connect single MCP server."""
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

                with self._lock:
                    self.sessions[name] = session

                    # Get tool list
                    tools_result = await session.list_tools()
                    for tool in tools_result.tools:
                        self.tools.append(Tool(
                            name=tool.name,
                            description=tool.description or "",
                            input_schema=tool.inputSchema or {},
                        ))

    def is_connected(self) -> bool:
        """Check if connection is complete."""
        with self._lock:
            return self._connected

    def is_connecting(self) -> bool:
        """Check if connection is in progress."""
        with self._lock:
            return self._connecting

    def call_tool_sync(self, call: ToolCall) -> ToolResult:
        """Sync tool call."""
        try:
            return asyncio.run(self._call_tool_async(call))
        except Exception as e:
            return ToolResult(content=f"Error: {e}", is_error=True)

    async def _call_tool_async(self, call: ToolCall) -> ToolResult:
        """Call tool.

        Args:
            call: Tool call request

        Returns:
            ToolResult: Execution result
        """
        # Find the server that has this tool
        with self._lock:
            sessions_copy = dict(self.sessions)

        for name, session in sessions_copy.items():
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
        """Get all tool definitions for LLM."""
        with self._lock:
            return [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.input_schema.get("properties", {}),
                }
                for tool in self.tools
            ]

    def has_tools(self) -> bool:
        """Check if tools are available."""
        with self._lock:
            return len(self.tools) > 0

    def cleanup(self) -> None:
        """Cleanup resources on shutdown."""
        with self._lock:
            self.sessions.clear()
            self.tools.clear()
            self._connected = False

        if self._loop and self._loop.is_running():
            self._loop.stop()
