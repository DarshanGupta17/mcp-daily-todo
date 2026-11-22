from datetime import date
from typing import Optional

from fastapi import APIRouter, Query

from app.database.task_repository import TaskRepository

router = APIRouter(prefix="/api")


@router.get("/tasks")
async def get_tasks(
    date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None,
):
    tasks = await TaskRepository.list_tasks(
        task_date=date,
        start_date=start_date,
        end_date=end_date,
        status=status,
    )
    return {"tasks": tasks}


@router.get("/tasks/counts")
async def get_task_counts(
    start_date: str = Query(...),
    end_date: str = Query(...),
):
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    counts = await TaskRepository.counts_by_date(start, end)
    return {"counts": counts}


@router.get("/config/public")
async def public_config():
    from app.config import APP_TIMEZONE, GEMINI_MODEL

    from app.services.mcp_client import mcp_client

    return {
        "timezone": APP_TIMEZONE,
        "gemini_model": GEMINI_MODEL,
        "mcp_connected": mcp_client.connected,
    }