from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from study_planner_bot.repository.sqlite import SQLiteRepository
from study_planner_bot.services.planner import PlannerService


class PlannerServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        db_path = Path(self.tmp.name) / "planner.sqlite3"
        self.repo = SQLiteRepository(f"sqlite:///{db_path}")
        self.repo.init_schema()
        self.service = PlannerService(self.repo, ZoneInfo("Europe/Moscow"))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_add_task_with_due_and_reminder_creates_reminder(self) -> None:
        result = self.service.add_from_text(
            100,
            "task Реферат | due 01.09 18:00 | remind 31.08 10:00",
        )

        self.assertIsNotNone(result.task)
        self.assertIn("Задача добавлена", result.message)
        pending = self.repo.list_pending_reminders(
            datetime(2026, 8, 31, 9, 0, tzinfo=ZoneInfo("Europe/Moscow")),
            datetime(2026, 8, 31, 11, 0, tzinfo=ZoneInfo("Europe/Moscow")),
        )
        self.assertEqual(len(pending), 1)

    def test_add_schedule_item(self) -> None:
        result = self.service.add_from_text(100, "schedule mon 09:00 90 Математика")

        self.assertIsNotNone(result.schedule_item)
        items = self.repo.list_schedule_for_week(100)
        self.assertEqual(items[0].title, "Математика")
        self.assertEqual(items[0].day_of_week, 0)

    def test_callback_actions_update_task(self) -> None:
        result = self.service.add_from_text(100, "task Английский")
        task_id = result.task.id if result.task else 0

        self.assertIn("через 60 мин", self.service.snooze(100, task_id, 60, datetime(2026, 9, 1, 10, 0)))
        self.assertIn("завтра", self.service.reschedule_tomorrow(100, task_id, datetime(2026, 9, 1, 10, 0)))
        self.assertIn("выполненной", self.service.mark_done(100, task_id))
        self.assertEqual(self.repo.list_tasks(100), [])


if __name__ == "__main__":
    unittest.main()

