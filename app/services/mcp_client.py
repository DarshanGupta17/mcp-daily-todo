import json
import os
import sys
import time
from contextlib import AsyncExitStack
from typing import Any, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from app.config import BASE_DIR, MCP_SERVER_MODULE
from app.services.event_bus import event_bus, iso_now
from app.services.schema_adapter import mcp_schema_to_gemini_parameters


class MCPClientService:
    def __init__(self) -> None:
        self._stack: Optional[AsyncExitStack] = None
        self._session: Optional[ClientSession] = None
        self._connected = False
        self.tools: list[Any] = []
        self._tool_execution_counts: dict[str, int] = {}

    @property
    def connected(self) -> bool:
        return self._connected

    def execution_count(self, tool_name: str) -> int:
        return self._tool_execution_counts.get(tool_name, 0)

    async def connect(self) -> None:
        child_env = os.environ.copy()
        child_env["PYTHONPATH"] = os.pathsep.join(
            [str(BASE_DIR), child_env.get("PYTHONPATH", "")]
        ).strip(os.pathsep)
        server_params = StdioServerParameters(
            command=sys.executable,
            args=["-m", MCP_SERVER_MODULE],
            cwd=str(BASE_DIR),
            env=child_env,
        )
        self._stack = AsyncExitStack()
        read, write = await self._stack.enter_async_context(stdio_client(server_params))
        self._session = await self._stack.enter_async_context(ClientSession(read, write))
        await self._session.initialize()
        result = await self._session.list_tools()
        self.tools = list(result.tools)
        self._connected = True
        for t in self.tools:
            self._tool_execution_counts[t.name] = 0

    async def disconnect(self) -> None:
        if self._stack:
            await self._stack.aclose()
        self._stack = None
        self._session = None
        self._connected = False

    def mcp_tools_to_gemini(self) -> list[dict[str, Any]]:
        declarations = []
        for tool in self.tools:
            declarations.append(
                {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": mcp_schema_to_gemini_parameters(
                        tool.inputSchema if hasattr(tool, "inputSchema") else None
                    ),
                }
            )
        return declarations

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        *,
        request_id: Optional[str] = None,
    ) -> dict[str, Any]:
        if not self._session:
            raise RuntimeError("MCP client not connected")

        execution_id = str(uuid4_safe())
        started = time.perf_counter()
        await event_bus.emit(
            {
                "event": "tool_started",
                "execution_id": execution_id,
                "request_id": request_id,
                "tool_name": name,
                "arguments": arguments,
                "timestamp": iso_now(),
            }
        )

        try:
            result = await self._session.call_tool(name, arguments)
            duration_ms = int((time.perf_counter() - started) * 1000)
            self._tool_execution_counts[name] = self._tool_execution_counts.get(name, 0) + 1
            event_bus.total_tool_executions += 1

            parsed = parse_tool_result(result)
            success = bool(parsed.get("success", True))
            status = "success" if success else "failed"
            await event_bus.emit(
                {
                    "event": "tool_completed" if success else "tool_failed",
                    "execution_id": execution_id,
                    "request_id": request_id,
                    "tool_name": name,
                    "status": status,
                    "arguments": arguments,
                    "result": parsed,
                    "duration_ms": duration_ms,
                    "timestamp": iso_now(),
                }
            )
            if success and _task_mutation_tool(name):
                await event_bus.emit({"event": "tasks_changed", "request_id": request_id})
            return parsed
        except Exception as e:
            duration_ms = int((time.perf_counter() - started) * 1000)
            await event_bus.emit(
                {
                    "event": "tool_failed",
                    "execution_id": execution_id,
                    "request_id": request_id,
                    "tool_name": name,
                    "status": "failed",
                    "arguments": arguments,
                    "result": {"success": False, "message": str(e)},
                    "duration_ms": duration_ms,
                    "timestamp": iso_now(),
                }
            )
            raise


def uuid4_safe() -> str:
    from uuid import uuid4

    return str(uuid4())


def parse_tool_result(result: Any) -> dict[str, Any]:
    if result.isError:
        texts = [c.text for c in result.content if hasattr(c, "text")]
        return {"success": False, "message": " ".join(texts) or "Tool error"}
    structured = getattr(result, "structuredContent", None)
    if isinstance(structured, dict):
        return structured
    for block in result.content:
        if hasattr(block, "text"):
            try:
                return json.loads(block.text)
            except json.JSONDecodeError:
                return {"success": True, "message": block.text}
    return {"success": True}


def _task_mutation_tool(name: str) -> bool:
    return name in {
        "create_task",
        "update_task",
        "delete_task",
        "complete_task",
        "reopen_task",
    }


mcp_client = MCPClientService()