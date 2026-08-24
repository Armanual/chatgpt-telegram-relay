from __future__ import annotations

from datetime import datetime, timedelta

from study_planner_bot.config import Settings
from study_planner_bot.models import Reminder, ReminderKind
from study_planner_bot.repository.base import Repository
from study_planner_bot.services.formatting import (
    format_evening_summary,
    format_task,
    format_today_plan,
    task_keyboard,
)
from study_planner_bot.time_utils import end_of_day, start_of_day


class ReminderService:
    def __init__(self, repo: Repository, settings: Settings) -> None:
        self.repo = repo
        self.settings = settings

    def ensure_daily_reminders(self, current_time: datetime) -> int:
        created = 0
        chat_ids = self.repo.list_known_chat_ids()
        if self.settings.telegram_default_chat_id and self.settings.telegram_default_chat_id not in chat_ids:
            chat_ids.append(self.settings.telegram_default_chat_id)
        for chat_id in chat_ids:
            for kind, hour in (
                (ReminderKind.DAILY_PLAN, self.settings.morning_plan_hour),
                (ReminderKind.EVENING_SUMMARY, self.settings.evening_summary_hour),
            ):
                if self.repo.daily_reminder_exists(chat_id, kind.value, current_time, hour):
                    continue
                remind_at = current_time.replace(hour=hour, minute=0, second=0, microsecond=0)
                if remind_at < current_time - timedelta(hours=1):
                    continue
                self.repo.create_reminder(
                    Reminder(
                        id=None,
                        chat_id=chat_id,
                        kind=kind,
                        target_id=None,
                        remind_at=remind_at,
                    )
                )
                created += 1
        return created

    def pending(self, current_time: datetime) -> list[Reminder]:
        end = current_time + timedelta(minutes=self.settings.reminder_lookahead_minutes)
        return self.repo.list_pending_reminders(current_time - timedelta(minutes=1), end)

    def render(self, reminder: Reminder, current_time: datetime) -> tuple[str, dict | None]:
        if reminder.kind == ReminderKind.DAILY_PLAN:
            schedule = self.repo.list_schedule_for_day(reminder.chat_id, current_time.weekday())
            tasks = self.repo.list_tasks_due_between(
                reminder.chat_id, start_of_day(current_time), end_of_day(current_time)
            )
            return format_today_plan(current_time, schedule, tasks, self.settings.timezone), None

        if reminder.kind == ReminderKind.EVENING_SUMMARY:
            open_tasks = self.repo.list_tasks(reminder.chat_id)
            return format_evening_summary(done_count=0, open_tasks=open_tasks, tz=self.settings.timezone), None

        if reminder.kind == ReminderKind.TASK and reminder.target_id:
            tasks = [task for task in self.repo.list_tasks(reminder.chat_id) if task.id == reminder.target_id]
            if tasks:
                task = tasks[0]
                return f"Напоминание по задаче\n\n{format_task(task, self.settings.timezone)}", task_keyboard(task.id or 0)
        return reminder.payload or "Напоминание", None

