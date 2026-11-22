import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable
from uuid import uuid4

EventHandler = Callable[[dict[str, Any]], Awaitable[None]]


class EventBus:

    def __init__(self) -> None:
        self._handlers: list[EventHandler] = []
        self._lock = asyncio.Lock()
        self.total_tool_executions = 0

    def subscribe(self, handler: EventHandler) -> None:
        self._handlers.append(handler)

    async def emit(self, event: dict[str, Any]) -> None:
        async with self._lock:
            for handler in self._handlers:
                await handler(event)


event_bus = EventBus()


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()