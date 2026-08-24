from __future__ import annotations

from datetime import datetime

from study_planner_bot.models import Reminder, ScheduleItem, StudyTask
from study_planner_bot.repository.base import Repository


class PostgresRepository(Repository):
    """Extension point for production storage.

    The app is already coded against the Repository interface. To enable Postgres,
    implement the methods here with psycopg, Neon, Supabase, or another hosted
    Postgres provider, then set DATABASE_URL to postgresql://...
    """

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def init_schema(self) -> None:
        self._not_implemented()

    def create_task(self, task: StudyTask) -> StudyTask:
        self._not_implemented()

    def list_tasks(self, chat_id: int, include_done: bool = False) -> list[StudyTask]:
        self._not_implemented()

    def list_tasks_due_between(
        self, chat_id: int, start: datetime, end: datetime, include_done: bool = False
    ) -> list[StudyTask]:
        self._not_implemented()

    def mark_task_done(self, chat_id: int, task_id: int) -> bool:
        self._not_implemented()

    def snooze_task(self, chat_id: int, task_id: int, remind_at: datetime) -> bool:
        self._not_implemented()

    def reschedule_task(self, chat_id: int, task_id: int, due_at: datetime) -> bool:
        self._not_implemented()

    def create_schedule_item(self, item: ScheduleItem) -> ScheduleItem:
        self._not_implemented()

    def list_schedule_for_day(self, chat_id: int, day_of_week: int) -> list[ScheduleItem]:
        self._not_implemented()

    def list_schedule_for_week(self, chat_id: int) -> list[ScheduleItem]:
        self._not_implemented()

    def create_reminder(self, reminder: Reminder) -> Reminder:
        self._not_implemented()

    def list_pending_reminders(self, start: datetime, end: datetime, limit: int = 100) -> list[Reminder]:
        self._not_implemented()

    def mark_reminder_sent(self, reminder_id: int, sent_at: datetime) -> bool:
        self._not_implemented()

    def daily_reminder_exists(self, chat_id: int, kind: str, day: datetime, hour: int) -> bool:
        self._not_implemented()

    def list_known_chat_ids(self) -> list[int]:
        self._not_implemented()

    def _not_implemented(self):
        raise NotImplementedError(
            "PostgresRepository is a ready extension point. "
            "Implement it before using postgresql:// DATABASE_URL in production."
        )
