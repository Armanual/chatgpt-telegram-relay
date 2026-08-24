from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

from study_planner_bot.models import ScheduleItem, StudyTask
from study_planner_bot.time_utils import DAY_NAMES_RU, format_dt, format_time


def format_task(task: StudyTask, tz: ZoneInfo) -> str:
    due = format_dt(task.due_at, tz)
    return f"#{task.id} {task.title} - дедлайн: {due}"


def format_tasks(title: str, tasks: list[StudyTask], tz: ZoneInfo) -> str:
    if not tasks:
        return f"{title}\n\nПока пусто."
    lines = [title, ""]
    lines.extend(format_task(task, tz) for task in tasks)
    return "\n".join(lines)


def format_schedule_day(title: str, items: list[ScheduleItem]) -> str:
    if not items:
        return f"{title}\n\nВ расписании пока ничего нет."
    lines = [title, ""]
    for item in items:
        location = f" · {item.location}" if item.location else ""
        lines.append(
            f"{format_time(item.start_time)} · {item.title} · {item.duration_minutes} мин{location}"
        )
    return "\n".join(lines)


def format_schedule_week(items: list[ScheduleItem]) -> str:
    if not items:
        return "Расписание на неделю\n\nПока пусто. Когда учеба начнётся, добавим пары сюда."
    grouped: dict[int, list[ScheduleItem]] = defaultdict(list)
    for item in items:
        grouped[item.day_of_week].append(item)
    lines = ["Расписание на неделю", ""]
    for day in range(7):
        if day not in grouped:
            continue
        lines.append(DAY_NAMES_RU[day].capitalize())
        for item in grouped[day]:
            lines.append(f"  {format_time(item.start_time)} · {item.title}")
        lines.append("")
    return "\n".join(lines).strip()


def format_today_plan(
    current_time: datetime,
    schedule_items: list[ScheduleItem],
    tasks_due_today: list[StudyTask],
    tz: ZoneInfo,
) -> str:
    lines = [f"План на сегодня · {current_time.strftime('%d.%m.%Y')}", ""]
    if schedule_items:
        lines.append("Расписание:")
        for item in schedule_items:
            lines.append(f"- {format_time(item.start_time)} · {item.title}")
    else:
        lines.append("Расписание: пока пусто.")
    lines.append("")
    if tasks_due_today:
        lines.append("Дедлайны и задачи:")
        for task in tasks_due_today:
            lines.append(f"- {format_task(task, tz)}")
    else:
        lines.append("Дедлайны и задачи: на сегодня ничего срочного.")
    return "\n".join(lines)


def format_evening_summary(done_count: int, open_tasks: list[StudyTask], tz: ZoneInfo) -> str:
    lines = ["Вечерний итог", "", f"Выполнено сегодня: {done_count}"]
    if open_tasks:
        lines.append("")
        lines.append("Осталось в открытых задачах:")
        for task in open_tasks[:10]:
            lines.append(f"- {format_task(task, tz)}")
    else:
        lines.append("")
        lines.append("Открытых задач нет.")
    return "\n".join(lines)


def task_keyboard(task_id: int) -> dict:
    return {
        "inline_keyboard": [
            [
                {"text": "Done", "callback_data": f"done:{task_id}"},
                {"text": "Snooze", "callback_data": f"snooze:{task_id}:60"},
                {"text": "Reschedule", "callback_data": f"reschedule:{task_id}:tomorrow"},
            ]
        ]
    }

