import sys
from pathlib import Path
from typing import Optional

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from mcp.server.fastmcp import FastMCP

from app.database.database import init_db
from app.mcp_server.tools import (
    handle_complete_task,
    handle_create_task,
    handle_delete_task,
    handle_list_tasks,
    handle_reopen_task,
    handle_update_task,
)

mcp = FastMCP("mcp-playground-tasks")


@mcp.tool(description="Creates a new task on a specified date.")
async def create_task(title: str, date: str, description: str = "") -> dict:
    return await handle_create_task(
        {"title": title, "date": date, "description": description}
    )


@mcp.tool(
    description="Lists tasks for a date or date range, with optional status filter."
)
async def list_tasks(
    date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None,
) -> dict:
    return await handle_list_tasks(
        {
            "date": date,
            "start_date": start_date,
            "end_date": end_date,
            "status": status,
        }
    )


@mcp.tool(description="Updates an existing task. Only supplied fields are changed.")
async def update_task(
    task_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    date: Optional[str] = None,
) -> dict:
    return await handle_update_task(
        {
            "task_id": task_id,
            "title": title,
            "description": description,
            "date": date,
        }
    )


@mcp.tool(description="Deletes a task by ID.")
async def delete_task(task_id: int) -> dict:
    return await handle_delete_task({"task_id": task_id})


@mcp.tool(description="Marks a task as completed.")
async def complete_task(task_id: int) -> dict:
    return await handle_complete_task({"task_id": task_id})


@mcp.tool(description="Marks a completed task as pending.")
async def reopen_task(task_id: int) -> dict:
    return await handle_reopen_task({"task_id": task_id})


if __name__ == "__main__":
    import asyncio

    async def startup() -> None:
        await init_db()

    asyncio.run(startup())
    mcp.run(transport="stdio")