from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from study_planner_bot.config import Settings
from study_planner_bot.repository.base import Repository
from study_planner_bot.services.formatting import (
    format_schedule_day,
    format_schedule_week,
    format_tasks,
    format_today_plan,
    task_keyboard,
)
from study_planner_bot.services.planner import PlannerService, add_help
from study_planner_bot.time_utils import end_of_day, now_in, start_of_day

if TYPE_CHECKING:
    from study_planner_bot.telegram.client import TelegramClient


class TelegramUpdateHandler:
    def __init__(self, repo: Repository, client: TelegramClient, settings: Settings) -> None:
        self.repo = repo
        self.client = client
        self.settings = settings
        self.planner = PlannerService(repo, settings.timezone)

    async def handle(self, update: dict[str, Any]) -> dict[str, Any]:
        if "callback_query" in update:
            return await self._handle_callback(update["callback_query"])
        message = update.get("message") or update.get("edited_message")
        if not message:
            return {"ok": True, "ignored": True}
        chat_id = int(message["chat"]["id"])
        text = str(message.get("text") or "").strip()
        if not text:
            await self.client.send_message(chat_id, "Пока понимаю только текстовые команды.")
            return {"ok": True}
        return await self._handle_message(chat_id, text)

    async def _handle_message(self, chat_id: int, text: str) -> dict[str, Any]:
        current_time = now_in(self.settings.timezone)
        command, _, args = text.partition(" ")
        command = command.split("@", 1)[0].lower()

        if command == "/start":
            await self.client.send_message(chat_id, start_text())
        elif command == "/today":
            await self.client.send_message(chat_id, self._today_text(chat_id, current_time))
        elif command == "/week":
            await self.client.send_message(chat_id, format_schedule_week(self.repo.list_schedule_for_week(chat_id)))
        elif command == "/tasks":
            await self._send_tasks(chat_id)
        elif command == "/deadlines":
            tasks = [task for task in self.repo.list_tasks(chat_id) if task.due_at is not None]
            await self.client.send_message(chat_id, format_tasks("Ближайшие дедлайны", tasks, self.settings.timezone))
        elif command == "/add":
            try:
                result = self.planner.add_from_text(chat_id, args)
            except ValueError as exc:
                await self.client.send_message(chat_id, f"Не получилось добавить: {exc}\n\n{add_help()}")
            else:
                markup = task_keyboard(result.task.id) if result.task and result.task.id else None
                await self.client.send_message(chat_id, result.message, reply_markup=markup)
        else:
            await self.client.send_message(chat_id, "Не знаю такую команду.\n\n" + start_text())
        return {"ok": True}

    async def _send_tasks(self, chat_id: int) -> None:
        tasks = self.repo.list_tasks(chat_id)
        if not tasks:
            await self.client.send_message(chat_id, "Открытых задач нет.")
            return
        for task in tasks[:20]:
            await self.client.send_message(
                chat_id,
                format_tasks("Открытая задача", [task], self.settings.timezone),
                reply_markup=task_keyboard(task.id or 0),
            )

    def _today_text(self, chat_id: int, current_time: datetime) -> str:
        schedule = self.repo.list_schedule_for_day(chat_id, current_time.weekday())
        tasks = self.repo.list_tasks_due_between(chat_id, start_of_day(current_time), end_of_day(current_time))
        if schedule or tasks:
            return format_today_plan(current_time, schedule, tasks, self.settings.timezone)
        return format_schedule_day("Сегодня", schedule)

    async def _handle_callback(self, callback: dict[str, Any]) -> dict[str, Any]:
        callback_id = str(callback["id"])
        chat_id = int(callback["message"]["chat"]["id"])
        data = str(callback.get("data") or "")
        current_time = now_in(self.settings.timezone)
        parts = data.split(":")
        result = "Не понял кнопку."
        if len(parts) >= 2 and parts[0] == "done":
            result = self.planner.mark_done(chat_id, int(parts[1]))
        elif len(parts) >= 3 and parts[0] == "snooze":
            result = self.planner.snooze(chat_id, int(parts[1]), int(parts[2]), current_time)
        elif len(parts) >= 3 and parts[0] == "reschedule" and parts[2] == "tomorrow":
            result = self.planner.reschedule_tomorrow(chat_id, int(parts[1]), current_time)
        await self.client.answer_callback_query(callback_id, result)
        await self.client.send_message(chat_id, result)
        return {"ok": True}


def start_text() -> str:
    return (
        "Я учебный планировщик: расписание, задачи, дедлайны и напоминания.\n\n"
        "Команды:\n"
        "/today - план на сегодня\n"
        "/week - расписание недели\n"
        "/tasks - открытые задачи\n"
        "/deadlines - дедлайны\n"
        "/add - добавить задачу или пару\n\n"
        + add_help()
    )
