import asyncio
import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.event_bus import event_bus
from app.services.mcp_client import mcp_client

router = APIRouter()


class ConnectionManager:
    def __init__(self) -> None:
        self.active: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self.active.append(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            if websocket in self.active:
                self.active.remove(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        dead: list[WebSocket] = []
        payload = json.dumps(message)
        async with self._lock:
            sockets = list(self.active)
        for ws in sockets:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(ws)


manager = ConnectionManager()


async def _on_event(event: dict[str, Any]) -> None:
    await manager.broadcast(event)
    if event.get("event") in ("tool_completed", "tool_failed"):
        await manager.broadcast(
            {
                "event": "mcp_status",
                "connected": mcp_client.connected,
                "tool_count": len(mcp_client.tools),
                "total_executions": event_bus.total_tool_executions,
            }
        )
        await manager.broadcast(
            {
                "event": "tools_catalog",
                "tools": [
                    {
                        "name": t.name,
                        "description": t.description,
                        "inputSchema": t.inputSchema,
                        "execution_count": mcp_client.execution_count(t.name),
                    }
                    for t in mcp_client.tools
                ],
            }
        )


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        await manager.broadcast(
            {
                "event": "mcp_status",
                "connected": mcp_client.connected,
                "tool_count": len(mcp_client.tools),
                "total_executions": event_bus.total_tool_executions,
            }
        )
        await manager.broadcast(
            {
                "event": "tools_catalog",
                "tools": [
                    {
                        "name": t.name,
                        "description": t.description,
                        "inputSchema": t.inputSchema,
                        "execution_count": mcp_client.execution_count(t.name),
                    }
                    for t in mcp_client.tools
                ],
            }
        )
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)


def setup_event_bridge() -> None:
    event_bus.subscribe(_on_event)


async def broadcast_snapshot() -> None:
    await manager.broadcast(
        {
            "event": "mcp_status",
            "connected": mcp_client.connected,
            "tool_count": len(mcp_client.tools),
            "total_executions": event_bus.total_tool_executions,
        }
    )
    await manager.broadcast(
        {
            "event": "tools_catalog",
            "tools": [
                {
                    "name": t.name,
                    "description": t.description,
                    "inputSchema": t.inputSchema,
                    "execution_count": mcp_client.execution_count(t.name),
                }
                for t in mcp_client.tools
            ],
        }
    )