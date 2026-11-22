from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    task_date: date
    status: Literal["pending", "completed"] = "pending"


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    task_date: Optional[date] = None


class Task(TaskBase):
    id: int
    created_at: datetime
    updated_at: datetime


class TaskSummary(BaseModel):
    id: int
    title: str
    description: Optional[str]
    task_date: date
    status: str