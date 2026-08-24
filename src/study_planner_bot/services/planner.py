from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from study_planner_bot.models import Reminder, ReminderKind, ScheduleItem, StudyTask
from study_planner_bot.repository.base import Repository
from study_planner_bot.time_utils import parse_hhmm, parse_local_datetime


DAY_ALIASES = {
    "mon": 0,
    "monday": 0,
    "пн": 0,
    "понедельник": 0,
    "tue": 1,
    "tuesday": 1,
    "вт": 1,
    "вторник": 1,
    "wed": 2,
    "wednesday": 2,
    "ср": 2,
    "среда": 2,
    "thu": 3,
    "thursday": 3,
    "чт": 3,
    "четверг": 3,
    "fri": 4,
    "friday": 4,
    "пт": 4,
    "пятница": 4,
    "sat": 5,
    "saturday": 5,
    "сб": 5,
    "суббота": 5,
    "sun": 6,
    "sunday": 6,
    "вс": 6,
    "воскресенье": 6,
}


@dataclass(frozen=True)
class AddResult:
    message: str
    task: StudyTask | None = None
    schedule_item: ScheduleItem | None = None


class PlannerService:
    def __init__(self, repo: Repository, tz) -> None:
        self.repo = repo
        self.tz = tz

    def add_from_text(self, chat_id: int, raw: str) -> AddResult:
        text = raw.strip()
        if not text:
            return AddResult(message=add_help())
        if text.lower().startswith("schedule "):
            return self._add_schedule(chat_id, text[len("schedule ") :])
        if text.lower().startswith("task "):
            return self._add_task(chat_id, text[len("task ") :])
        return self._add_task(chat_id, text)

    def _add_task(self, chat_id: int, raw: str) -> AddResult:
        parts = [part.strip() for part in raw.split("|")]
        title = parts[0]
        if not title:
            return AddResult(message=add_help())
        due_at = None
        remind_at = None
        description = None
        for part in parts[1:]:
            key, _, value = part.partition(" ")
            key = key.lower()
            value = value.strip()
            if key == "due" and value:
                due_at = parse_local_datetime(value, self.tz)
            elif key == "remind" and value:
                remind_at = parse_local_datetime(value, self.tz)
            elif key in {"desc", "description"} and value:
                description = value
        task = self.repo.create_task(
            StudyTask(
                id=None,
                chat_id=chat_id,
                title=title,
                description=description,
                due_at=due_at,
                remind_at=remind_at,
            )
        )
        if task.remind_at:
            self.repo.create_reminder(
                Reminder(
                    id=None,
                    chat_id=chat_id,
                    kind=ReminderKind.TASK,
                    target_id=task.id,
                    remind_at=task.remind_at,
                    payload=task.title,
                )
            )
        return AddResult(message=f"Задача добавлена: #{task.id} {task.title}", task=task)

    def _add_schedule(self, chat_id: int, raw: str) -> AddResult:
        tokens = raw.split()
        if len(tokens) < 4:
            return AddResult(message=add_help())
        day = DAY_ALIASES.get(tokens[0].lower())
        if day is None:
            return AddResult(message="Не понял день недели. Например: /add schedule mon 09:00 90 Math")
        start_time = parse_hhmm(tokens[1])
        duration = int(tokens[2])
        title = " ".join(tokens[3:]).strip()
        item = self.repo.create_schedule_item(
            ScheduleItem(
                id=None,
                chat_id=chat_id,
                title=title,
                day_of_week=day,
                start_time=start_time,
                duration_minutes=duration,
            )
        )
        return AddResult(message=f"Расписание добавлено: {tokens[0]} {tokens[1]} · {title}", schedule_item=item)

    def mark_done(self, chat_id: int, task_id: int) -> str:
        if self.repo.mark_task_done(chat_id, task_id):
            return f"Готово: задача #{task_id} отмечена выполненной."
        return f"Не нашёл задачу #{task_id}."

    def snooze(self, chat_id: int, task_id: int, minutes: int, current_time: datetime) -> str:
        remind_at = current_time + timedelta(minutes=minutes)
        if self.repo.snooze_task(chat_id, task_id, remind_at):
            self.repo.create_reminder(
                Reminder(
                    id=None,
                    chat_id=chat_id,
                    kind=ReminderKind.TASK,
                    target_id=task_id,
                    remind_at=remind_at,
                    payload=f"snoozed:{task_id}",
                )
            )
            return f"Напомню о задаче #{task_id} через {minutes} мин."
        return f"Не нашёл задачу #{task_id}."

    def reschedule_tomorrow(self, chat_id: int, task_id: int, current_time: datetime) -> str:
        due_at = (current_time + timedelta(days=1)).replace(hour=18, minute=0, second=0, microsecond=0)
        if self.repo.reschedule_task(chat_id, task_id, due_at):
            return f"Перенёс задачу #{task_id} на завтра 18:00."
        return f"Не нашёл задачу #{task_id}."


def add_help() -> str:
    return (
        "Как добавлять:\n"
        "/add task Подготовить физику | due 01.09 18:00 | remind 31.08 10:00\n"
        "/add schedule mon 09:00 90 Математика"
    )

