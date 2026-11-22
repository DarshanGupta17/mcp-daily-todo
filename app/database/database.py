import aiosqlite

from app.config import DATABASE_PATH
from app.database.models import CREATE_TABLE_SQL


async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    return db


async def init_db() -> None:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(CREATE_TABLE_SQL)
        await db.commit()
        cursor = await db.execute("SELECT COUNT(*) FROM tasks")
        row = await cursor.fetchone()
        if row and row[0] == 0:
            await seed_tasks(db)


async def seed_tasks(db: aiosqlite.Connection) -> None:
    from datetime import timedelta
    from zoneinfo import ZoneInfo

    from app.config import APP_TIMEZONE

    today = __import__("datetime").datetime.now(ZoneInfo(APP_TIMEZONE)).date()
    samples = [
        ("Complete project documentation", 0, "pending"),
        ("Buy groceries", 0, "pending"),
        ("Call the client", 1, "pending"),
        ("Review pull requests", 1, "completed"),
        ("Pay electricity bill", 2, "pending"),
        ("Prepare presentation", 3, "pending"),
        ("Visit the bank", 4, "pending"),
        ("Finish backend development", 5, "pending"),
        ("Team standup", 6, "pending"),
        ("Weekly planning", -2, "completed"),
    ]
    for title, day_offset, status in samples:
        task_date = (today + timedelta(days=day_offset)).isoformat()
        await db.execute(
            """
            INSERT INTO tasks (title, description, task_date, status)
            VALUES (?, ?, ?, ?)
            """,
            (title, None, task_date, status),
        )
    await db.commit()