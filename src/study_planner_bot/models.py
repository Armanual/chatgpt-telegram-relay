from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from enum import StrEnum


class TaskStatus(StrEnum):
    OPEN = "open"
    DONE = "done"


class TaskPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class ReminderKind(StrEnum):
    TASK = "task"
    SCHEDULE = "schedule"
    DAILY_PLAN = "daily_plan"
    EVENING_SUMMARY = "evening_summary"


@dataclass(frozen=True)
class StudyTask:
    id: int | None
    chat_id: int
    title: str
    description: str | None = None
    due_at: datetime | None = None
    remind_at: datetime | None = None
    status: TaskStatus = TaskStatus.OPEN
    priority: TaskPriority = TaskPriority.NORMAL
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class ScheduleItem:
    id: int | None
    chat_id: int
    title: str
    day_of_week: int
    start_time: time
    duration_minutes: int
    location: str | None = None
    notes: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class Reminder:
    id: int | None
    chat_id: int
    kind: ReminderKind
    target_id: int | None
    remind_at: datetime
    payload: str | None = None
    sent_at: datetime | None = None
    created_at: datetime | None = None

