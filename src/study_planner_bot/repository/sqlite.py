from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, time
from pathlib import Path
from typing import Iterator

from study_planner_bot.models import (
    Reminder,
    ReminderKind,
    ScheduleItem,
    StudyTask,
    TaskPriority,
    TaskStatus,
)
from study_planner_bot.repository.base import Repository


class SQLiteRepository(Repository):
    def __init__(self, database_url: str) -> None:
        if not database_url.startswith("sqlite:///"):
            raise ValueError("SQLiteRepository expects DATABASE_URL like sqlite:///./data/app.db")
        raw_path = database_url.removeprefix("sqlite:///")
        self.path = Path(raw_path)
        if not self.path.is_absolute():
            self.path = Path.cwd() / self.path

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    due_at TEXT,
                    remind_at TEXT,
                    status TEXT NOT NULL DEFAULT 'open',
                    priority TEXT NOT NULL DEFAULT 'normal',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_tasks_chat_status_due
                    ON tasks(chat_id, status, due_at);

                CREATE TABLE IF NOT EXISTS schedule_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    day_of_week INTEGER NOT NULL CHECK(day_of_week BETWEEN 0 AND 6),
                    start_time TEXT NOT NULL,
                    duration_minutes INTEGER NOT NULL,
                    location TEXT,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_schedule_chat_day
                    ON schedule_items(chat_id, day_of_week, start_time);

                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    kind TEXT NOT NULL,
                    target_id INTEGER,
                    remind_at TEXT NOT NULL,
                    payload TEXT,
                    sent_at TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_reminders_pending
                    ON reminders(sent_at, remind_at);
                """
            )

    def create_task(self, task: StudyTask) -> StudyTask:
        now = _utcish_now()
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO tasks
                    (chat_id, title, description, due_at, remind_at, status, priority, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.chat_id,
                    task.title,
                    task.description,
                    _dt(task.due_at),
                    _dt(task.remind_at),
                    str(task.status),
                    str(task.priority),
                    _dt(now),
                    _dt(now),
                ),
            )
            task_id = int(cursor.lastrowid)
        return StudyTask(
            id=task_id,
            chat_id=task.chat_id,
            title=task.title,
            description=task.description,
            due_at=task.due_at,
            remind_at=task.remind_at,
            status=task.status,
            priority=task.priority,
            created_at=now,
            updated_at=now,
        )

    def list_tasks(self, chat_id: int, include_done: bool = False) -> list[StudyTask]:
        where = "chat_id = ?"
        params: list[object] = [chat_id]
        if not include_done:
            where += " AND status != ?"
            params.append(TaskStatus.DONE.value)
        return self._select_tasks(where, params, "ORDER BY due_at IS NULL, due_at, id")

    def list_tasks_due_between(
        self, chat_id: int, start: datetime, end: datetime, include_done: bool = False
    ) -> list[StudyTask]:
        where = "chat_id = ? AND due_at >= ? AND due_at < ?"
        params: list[object] = [chat_id, _dt(start), _dt(end)]
        if not include_done:
            where += " AND status != ?"
            params.append(TaskStatus.DONE.value)
        return self._select_tasks(where, params, "ORDER BY due_at, id")

    def mark_task_done(self, chat_id: int, task_id: int) -> bool:
        return self._update_task(
            "UPDATE tasks SET status = ?, updated_at = ? WHERE chat_id = ? AND id = ?",
            (TaskStatus.DONE.value, _dt(_utcish_now()), chat_id, task_id),
        )

    def snooze_task(self, chat_id: int, task_id: int, remind_at: datetime) -> bool:
        return self._update_task(
            "UPDATE tasks SET remind_at = ?, updated_at = ? WHERE chat_id = ? AND id = ?",
            (_dt(remind_at), _dt(_utcish_now()), chat_id, task_id),
        )

    def reschedule_task(self, chat_id: int, task_id: int, due_at: datetime) -> bool:
        return self._update_task(
            "UPDATE tasks SET due_at = ?, updated_at = ? WHERE chat_id = ? AND id = ?",
            (_dt(due_at), _dt(_utcish_now()), chat_id, task_id),
        )

    def create_schedule_item(self, item: ScheduleItem) -> ScheduleItem:
        now = _utcish_now()
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO schedule_items
                    (chat_id, title, day_of_week, start_time, duration_minutes, location, notes,
                     created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.chat_id,
                    item.title,
                    item.day_of_week,
                    item.start_time.strftime("%H:%M:%S"),
                    item.duration_minutes,
                    item.location,
                    item.notes,
                    _dt(now),
                    _dt(now),
                ),
            )
            item_id = int(cursor.lastrowid)
        return ScheduleItem(
            id=item_id,
            chat_id=item.chat_id,
            title=item.title,
            day_of_week=item.day_of_week,
            start_time=item.start_time,
            duration_minutes=item.duration_minutes,
            location=item.location,
            notes=item.notes,
            created_at=now,
            updated_at=now,
        )

    def list_schedule_for_day(self, chat_id: int, day_of_week: int) -> list[ScheduleItem]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM schedule_items
                WHERE chat_id = ? AND day_of_week = ?
                ORDER BY start_time, id
                """,
                (chat_id, day_of_week),
            ).fetchall()
        return [_schedule_from_row(row) for row in rows]

    def list_schedule_for_week(self, chat_id: int) -> list[ScheduleItem]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM schedule_items
                WHERE chat_id = ?
                ORDER BY day_of_week, start_time, id
                """,
                (chat_id,),
            ).fetchall()
        return [_schedule_from_row(row) for row in rows]

    def create_reminder(self, reminder: Reminder) -> Reminder:
        now = _utcish_now()
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO reminders
                    (chat_id, kind, target_id, remind_at, payload, sent_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    reminder.chat_id,
                    str(reminder.kind),
                    reminder.target_id,
                    _dt(reminder.remind_at),
                    reminder.payload,
                    _dt(reminder.sent_at),
                    _dt(now),
                ),
            )
            reminder_id = int(cursor.lastrowid)
        return Reminder(
            id=reminder_id,
            chat_id=reminder.chat_id,
            kind=reminder.kind,
            target_id=reminder.target_id,
            remind_at=reminder.remind_at,
            payload=reminder.payload,
            sent_at=reminder.sent_at,
            created_at=now,
        )

    def list_pending_reminders(self, start: datetime, end: datetime, limit: int = 100) -> list[Reminder]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM reminders
                WHERE sent_at IS NULL AND remind_at >= ? AND remind_at <= ?
                ORDER BY remind_at, id
                LIMIT ?
                """,
                (_dt(start), _dt(end), limit),
            ).fetchall()
        return [_reminder_from_row(row) for row in rows]

    def mark_reminder_sent(self, reminder_id: int, sent_at: datetime) -> bool:
        with self.connect() as conn:
            cursor = conn.execute(
                "UPDATE reminders SET sent_at = ? WHERE id = ?",
                (_dt(sent_at), reminder_id),
            )
        return cursor.rowcount > 0

    def daily_reminder_exists(self, chat_id: int, kind: str, day: datetime, hour: int) -> bool:
        start = day.replace(hour=hour, minute=0, second=0, microsecond=0)
        end = start.replace(minute=59, second=59)
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT 1 FROM reminders
                WHERE chat_id = ? AND kind = ? AND remind_at >= ? AND remind_at <= ?
                LIMIT 1
                """,
                (chat_id, kind, _dt(start), _dt(end)),
            ).fetchone()
        return row is not None

    def list_known_chat_ids(self) -> list[int]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT chat_id FROM tasks
                UNION
                SELECT chat_id FROM schedule_items
                UNION
                SELECT chat_id FROM reminders
                ORDER BY chat_id
                """
            ).fetchall()
        return [int(row["chat_id"]) for row in rows]

    def _select_tasks(self, where: str, params: list[object], order_by: str) -> list[StudyTask]:
        with self.connect() as conn:
            rows = conn.execute(f"SELECT * FROM tasks WHERE {where} {order_by}", params).fetchall()
        return [_task_from_row(row) for row in rows]

    def _update_task(self, sql: str, params: tuple[object, ...]) -> bool:
        with self.connect() as conn:
            cursor = conn.execute(sql, params)
        return cursor.rowcount > 0


def _dt(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _parse_dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _parse_time(value: str) -> time:
    return time.fromisoformat(value)


def _utcish_now() -> datetime:
    return datetime.now().replace(microsecond=0)


def _task_from_row(row: sqlite3.Row) -> StudyTask:
    return StudyTask(
        id=int(row["id"]),
        chat_id=int(row["chat_id"]),
        title=str(row["title"]),
        description=row["description"],
        due_at=_parse_dt(row["due_at"]),
        remind_at=_parse_dt(row["remind_at"]),
        status=TaskStatus(row["status"]),
        priority=TaskPriority(row["priority"]),
        created_at=_parse_dt(row["created_at"]),
        updated_at=_parse_dt(row["updated_at"]),
    )


def _schedule_from_row(row: sqlite3.Row) -> ScheduleItem:
    return ScheduleItem(
        id=int(row["id"]),
        chat_id=int(row["chat_id"]),
        title=str(row["title"]),
        day_of_week=int(row["day_of_week"]),
        start_time=_parse_time(str(row["start_time"])),
        duration_minutes=int(row["duration_minutes"]),
        location=row["location"],
        notes=row["notes"],
        created_at=_parse_dt(row["created_at"]),
        updated_at=_parse_dt(row["updated_at"]),
    )


def _reminder_from_row(row: sqlite3.Row) -> Reminder:
    return Reminder(
        id=int(row["id"]),
        chat_id=int(row["chat_id"]),
        kind=ReminderKind(row["kind"]),
        target_id=row["target_id"],
        remind_at=datetime.fromisoformat(row["remind_at"]),
        payload=row["payload"],
        sent_at=_parse_dt(row["sent_at"]),
        created_at=_parse_dt(row["created_at"]),
    )

