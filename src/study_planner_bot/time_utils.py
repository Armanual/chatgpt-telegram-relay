from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo


DAY_NAMES_RU = {
    0: "понедельник",
    1: "вторник",
    2: "среда",
    3: "четверг",
    4: "пятница",
    5: "суббота",
    6: "воскресенье",
}


def now_in(tz: ZoneInfo) -> datetime:
    return datetime.now(tz=tz).replace(microsecond=0)


def ensure_tz(value: datetime, tz: ZoneInfo) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=tz)
    return value.astimezone(tz)


def parse_local_datetime(text: str, tz: ZoneInfo) -> datetime:
    clean = text.strip().replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M", "%d.%m.%Y %H:%M", "%d.%m %H:%M"):
        try:
            parsed = datetime.strptime(clean, fmt)
            if fmt == "%d.%m %H:%M":
                parsed = parsed.replace(year=now_in(tz).year)
            return parsed.replace(tzinfo=tz)
        except ValueError:
            continue
    raise ValueError("Expected datetime like 2026-09-01 18:00 or 01.09 18:00")


def parse_hhmm(text: str) -> time:
    return datetime.strptime(text.strip(), "%H:%M").time()


def start_of_day(value: datetime) -> datetime:
    return value.replace(hour=0, minute=0, second=0, microsecond=0)


def end_of_day(value: datetime) -> datetime:
    return start_of_day(value) + timedelta(days=1)


def format_dt(value: datetime | None, tz: ZoneInfo) -> str:
    if value is None:
        return "без даты"
    local = ensure_tz(value, tz)
    return local.strftime("%d.%m.%Y %H:%M")


def format_time(value: time) -> str:
    return value.strftime("%H:%M")

