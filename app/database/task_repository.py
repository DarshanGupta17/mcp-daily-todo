from datetime import date, datetime
from typing import Any, Optional

import aiosqlite

from app.config import DATABASE_PATH


def _row_to_dict(row: aiosqlite.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "task_date": row["task_date"],
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


class TaskRepository:
    @staticmethod
    async def create(
        title: str, task_date: str, description: Optional[str] = None
    ) -> dict[str, Any]:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                INSERT INTO tasks (title, description, task_date, status)
                VALUES (?, ?, ?, 'pending')
                """,
                (title, description or "", task_date),
            )
            await db.commit()
            task_id = cursor.lastrowid
            cursor = await db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = await cursor.fetchone()
            return _row_to_dict(row)

    @staticmethod
    async def get_by_id(task_id: int) -> Optional[dict[str, Any]]:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = await cursor.fetchone()
            return _row_to_dict(row) if row else None

    @staticmethod
    async def list_tasks(
        task_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM tasks WHERE 1=1"
        params: list[Any] = []

        if task_date:
            query += " AND task_date = ?"
            params.append(task_date)
        elif start_date and end_date:
            query += " AND task_date >= ? AND task_date <= ?"
            params.extend([start_date, end_date])

        if status and status != "all":
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY task_date ASC, id ASC"

        async with aiosqlite.connect(DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [_row_to_dict(r) for r in rows]

    @staticmethod
    async def update(
        task_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        task_date: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        existing = await TaskRepository.get_by_id(task_id)
        if not existing:
            return None

        fields = []
        params: list[Any] = []
        if title is not None:
            fields.append("title = ?")
            params.append(title)
        if description is not None:
            fields.append("description = ?")
            params.append(description)
        if task_date is not None:
            fields.append("task_date = ?")
            params.append(task_date)

        if not fields:
            return existing

        fields.append("updated_at = ?")
        params.append(datetime.utcnow().isoformat())
        params.append(task_id)

        async with aiosqlite.connect(DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row
            await db.execute(
                f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?",
                params,
            )
            await db.commit()
        return await TaskRepository.get_by_id(task_id)

    @staticmethod
    async def delete(task_id: int) -> bool:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            await db.commit()
            return cursor.rowcount > 0

    @staticmethod
    async def complete(task_id: int) -> Optional[dict[str, Any]]:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute(
                "UPDATE tasks SET status = 'completed', updated_at = ? WHERE id = ?",
                (datetime.utcnow().isoformat(), task_id),
            )
            await db.commit()
            if cursor.rowcount == 0:
                return None
        return await TaskRepository.get_by_id(task_id)

    @staticmethod
    async def reopen(task_id: int) -> Optional[dict[str, Any]]:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute(
                "UPDATE tasks SET status = 'pending', updated_at = ? WHERE id = ?",
                (datetime.utcnow().isoformat(), task_id),
            )
            await db.commit()
            if cursor.rowcount == 0:
                return None
        return await TaskRepository.get_by_id(task_id)

    @staticmethod
    async def counts_by_date(start: date, end: date) -> dict[str, int]:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute(
                """
                SELECT task_date, COUNT(*) as cnt
                FROM tasks
                WHERE task_date >= ? AND task_date <= ?
                GROUP BY task_date
                """,
                (start.isoformat(), end.isoformat()),
            )
            rows = await cursor.fetchall()
            return {row[0]: row[1] for row in rows}