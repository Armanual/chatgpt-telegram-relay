from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from study_planner_bot.models import Reminder, ReminderKind, ScheduleItem, StudyTask, TaskStatus
from study_planner_bot.repository.sqlite import SQLiteRepository
from study_planner_bot.time_utils import parse_hhmm


class SQLiteRepositoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        db_path = Path(self.tmp.name) / "test.sqlite3"
        self.repo = SQLiteRepository(f"sqlite:///{db_path}")
        self.repo.init_schema()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_tasks_can_be_created_listed_and_completed(self) -> None:
        tz = ZoneInfo("Europe/Moscow")
        task = self.repo.create_task(
            StudyTask(
                id=None,
                chat_id=100,
                title="Подготовить физику",
                due_at=datetime(2026, 9, 1, 18, 0, tzinfo=tz),
            )
        )

        self.assertIsNotNone(task.id)
        self.assertEqual(len(self.repo.list_tasks(100)), 1)

        self.assertTrue(self.repo.mark_task_done(100, task.id or 0))
        self.assertEqual(self.repo.list_tasks(100), [])
        done_task = self.repo.list_tasks(100, include_done=True)[0]
        self.assertEqual(done_task.status, TaskStatus.DONE)

    def test_schedule_items_are_ordered_by_time(self) -> None:
        self.repo.create_schedule_item(
            ScheduleItem(
                id=None,
                chat_id=100,
                title="История",
                day_of_week=0,
                start_time=parse_hhmm("11:00"),
                duration_minutes=90,
            )
        )
        self.repo.create_schedule_item(
            ScheduleItem(
                id=None,
                chat_id=100,
                title="Математика",
                day_of_week=0,
                start_time=parse_hhmm("09:00"),
                duration_minutes=90,
            )
        )

        items = self.repo.list_schedule_for_day(100, 0)
        self.assertEqual([item.title for item in items], ["Математика", "История"])

    def test_pending_reminders_are_filtered(self) -> None:
        tz = ZoneInfo("Europe/Moscow")
        reminder = self.repo.create_reminder(
            Reminder(
                id=None,
                chat_id=100,
                kind=ReminderKind.TASK,
                target_id=1,
                remind_at=datetime(2026, 9, 1, 10, 0, tzinfo=tz),
            )
        )

        pending = self.repo.list_pending_reminders(
            datetime(2026, 9, 1, 9, 55, tzinfo=tz),
            datetime(2026, 9, 1, 10, 15, tzinfo=tz),
        )
        self.assertEqual([item.id for item in pending], [reminder.id])

        self.repo.mark_reminder_sent(reminder.id or 0, datetime(2026, 9, 1, 10, 1, tzinfo=tz))
        self.assertEqual(
            self.repo.list_pending_reminders(
                datetime(2026, 9, 1, 9, 55, tzinfo=tz),
                datetime(2026, 9, 1, 10, 15, tzinfo=tz),
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()

