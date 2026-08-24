from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from study_planner_bot.config import Settings
from study_planner_bot.repository.sqlite import SQLiteRepository
from study_planner_bot.telegram.handlers import TelegramUpdateHandler


class FakeTelegramClient:
    def __init__(self) -> None:
        self.messages: list[dict] = []
        self.callbacks: list[dict] = []

    async def send_message(self, chat_id: int, text: str, reply_markup=None, parse_mode=None) -> dict:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "reply_markup": reply_markup,
            "parse_mode": parse_mode,
        }
        self.messages.append(payload)
        return {"ok": True, "payload": payload}

    async def answer_callback_query(self, callback_query_id: str, text: str) -> dict:
        payload = {"callback_query_id": callback_query_id, "text": text}
        self.callbacks.append(payload)
        return {"ok": True, "payload": payload}


class TelegramHandlerTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        db_path = Path(self.tmp.name) / "handler.sqlite3"
        self.repo = SQLiteRepository(f"sqlite:///{db_path}")
        self.repo.init_schema()
        self.client = FakeTelegramClient()
        self.handler = TelegramUpdateHandler(self.repo, self.client, test_settings())

    def tearDown(self) -> None:
        self.tmp.cleanup()

    async def test_add_task_and_done_callback(self) -> None:
        await self.handler.handle(
            {
                "message": {
                    "chat": {"id": 100},
                    "text": "/add task Литература | due 01.09 18:00",
                }
            }
        )

        tasks = self.repo.list_tasks(100)
        self.assertEqual(len(tasks), 1)
        self.assertIn("Задача добавлена", self.client.messages[-1]["text"])

        await self.handler.handle(
            {
                "callback_query": {
                    "id": "callback-1",
                    "message": {"chat": {"id": 100}},
                    "data": f"done:{tasks[0].id}",
                }
            }
        )

        self.assertEqual(self.repo.list_tasks(100), [])
        self.assertIn("выполненной", self.client.callbacks[-1]["text"])


def test_settings() -> Settings:
    return Settings(
        telegram_bot_token=None,
        telegram_default_chat_id=None,
        telegram_webhook_secret="webhook-secret",
        relay_secret="relay-secret",
        cron_secret="cron-secret",
        app_env="test",
        app_timezone="Europe/Moscow",
        database_url="sqlite:///unused.sqlite3",
        reminder_lookahead_minutes=15,
        morning_plan_hour=8,
        evening_summary_hour=21,
    )


if __name__ == "__main__":
    unittest.main()

