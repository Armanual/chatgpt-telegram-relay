from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, time

from study_planner_bot.models import Reminder, ScheduleItem, StudyTask


class Repository(ABC):
    @abstractmethod
    def init_schema(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def create_task(self, task: StudyTask) -> StudyTask:
        raise NotImplementedError

    @abstractmethod
    def list_tasks(self, chat_id: int, include_done: bool = False) -> list[StudyTask]:
        raise NotImplementedError

    @abstractmethod
    def list_tasks_due_between(
        self, chat_id: int, start: datetime, end: datetime, include_done: bool = False
    ) -> list[StudyTask]:
        raise NotImplementedError

    @abstractmethod
    def mark_task_done(self, chat_id: int, task_id: int) -> bool:
        raise NotImplementedError

    @abstractmethod
    def snooze_task(self, chat_id: int, task_id: int, remind_at: datetime) -> bool:
        raise NotImplementedError

    @abstractmethod
    def reschedule_task(self, chat_id: int, task_id: int, due_at: datetime) -> bool:
        raise NotImplementedError

    @abstractmethod
    def create_schedule_item(self, item: ScheduleItem) -> ScheduleItem:
        raise NotImplementedError

    @abstractmethod
    def list_schedule_for_day(self, chat_id: int, day_of_week: int) -> list[ScheduleItem]:
        raise NotImplementedError

    @abstractmethod
    def list_schedule_for_week(self, chat_id: int) -> list[ScheduleItem]:
        raise NotImplementedError

    @abstractmethod
    def create_reminder(self, reminder: Reminder) -> Reminder:
        raise NotImplementedError

    @abstractmethod
    def list_pending_reminders(self, start: datetime, end: datetime, limit: int = 100) -> list[Reminder]:
        raise NotImplementedError

    @abstractmethod
    def mark_reminder_sent(self, reminder_id: int, sent_at: datetime) -> bool:
        raise NotImplementedError

    @abstractmethod
    def daily_reminder_exists(self, chat_id: int, kind: str, day: datetime, hour: int) -> bool:
        raise NotImplementedError

    @abstractmethod
    def list_known_chat_ids(self) -> list[int]:
        raise NotImplementedError


def serialize_time(value: time) -> str:
    return value.strftime("%H:%M:%S")

