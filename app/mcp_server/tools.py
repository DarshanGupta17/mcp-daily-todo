import json
from typing import Any

from app.database.task_repository import TaskRepository


async def handle_create_task(arguments: dict[str, Any]) -> dict[str, Any]:
    title = arguments.get("title")
    task_date = arguments.get("date")
    if not title or not task_date:
        return {"success": False, "message": "title and date are required"}
    description = arguments.get("description", "")
    task = await TaskRepository.create(title, task_date, description)
    return {
        "success": True,
        "task_id": task["id"],
        "message": "Task created successfully",
        "task": task,
    }


async def handle_list_tasks(arguments: dict[str, Any]) -> dict[str, Any]:
    tasks = await TaskRepository.list_tasks(
        task_date=arguments.get("date"),
        start_date=arguments.get("start_date"),
        end_date=arguments.get("end_date"),
        status=arguments.get("status"),
    )
    return {"success": True, "count": len(tasks), "tasks": tasks}


async def handle_update_task(arguments: dict[str, Any]) -> dict[str, Any]:
    task_id = arguments.get("task_id")
    if task_id is None:
        return {"success": False, "message": "task_id is required"}
    updated = await TaskRepository.update(
        int(task_id),
        title=arguments.get("title"),
        description=arguments.get("description"),
        task_date=arguments.get("date"),
    )
    if not updated:
        return {"success": False, "message": f"Task {task_id} not found"}
    return {"success": True, "task": updated, "message": "Task updated successfully"}


async def handle_delete_task(arguments: dict[str, Any]) -> dict[str, Any]:
    task_id = arguments.get("task_id")
    if task_id is None:
        return {"success": False, "message": "task_id is required"}
    ok = await TaskRepository.delete(int(task_id))
    if not ok:
        return {"success": False, "message": f"Task {task_id} not found"}
    return {"success": True, "message": "Task deleted successfully", "task_id": int(task_id)}


async def handle_complete_task(arguments: dict[str, Any]) -> dict[str, Any]:
    task_id = arguments.get("task_id")
    if task_id is None:
        return {"success": False, "message": "task_id is required"}
    task = await TaskRepository.complete(int(task_id))
    if not task:
        return {"success": False, "message": f"Task {task_id} not found"}
    return {"success": True, "task": task, "message": "Task marked as completed"}


async def handle_reopen_task(arguments: dict[str, Any]) -> dict[str, Any]:
    task_id = arguments.get("task_id")
    if task_id is None:
        return {"success": False, "message": "task_id is required"}
    task = await TaskRepository.reopen(int(task_id))
    if not task:
        return {"success": False, "message": f"Task {task_id} not found"}
    return {"success": True, "task": task, "message": "Task reopened as pending"}


TOOL_HANDLERS = {
    "create_task": handle_create_task,
    "list_tasks": handle_list_tasks,
    "update_task": handle_update_task,
    "delete_task": handle_delete_task,
    "complete_task": handle_complete_task,
    "reopen_task": handle_reopen_task,
}


def tool_result_payload(data: dict[str, Any]) -> list[dict[str, str]]:
    return [{"type": "text", "text": json.dumps(data)}]