from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from zoneinfo import ZoneInfo

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency is installed in normal app environments.
    load_dotenv = None

if load_dotenv:
    load_dotenv()


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str | None
    telegram_default_chat_id: int | None
    telegram_webhook_secret: str | None
    relay_secret: str | None
    cron_secret: str | None
    app_env: str
    app_timezone: str
    database_url: str
    reminder_lookahead_minutes: int
    morning_plan_hour: int
    evening_summary_hour: int

    @property
    def timezone(self) -> ZoneInfo:
        return ZoneInfo(self.app_timezone)

    @property
    def has_telegram_token(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_bot_token != "replace-with-bot-token")

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


def _optional_int(value: str | None) -> int | None:
    if value is None or value.strip() == "":
        return None
    return int(value)


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
        telegram_default_chat_id=_optional_int(os.getenv("TELEGRAM_DEFAULT_CHAT_ID")),
        telegram_webhook_secret=os.getenv("TELEGRAM_WEBHOOK_SECRET"),
        relay_secret=os.getenv("RELAY_SECRET"),
        cron_secret=os.getenv("CRON_SECRET"),
        app_env=os.getenv("APP_ENV", "development"),
        app_timezone=os.getenv("APP_TIMEZONE", "Europe/Moscow"),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./data/study_planner.db"),
        reminder_lookahead_minutes=_int_env("REMINDER_LOOKAHEAD_MINUTES", 15),
        morning_plan_hour=_int_env("MORNING_PLAN_HOUR", 8),
        evening_summary_hour=_int_env("EVENING_SUMMARY_HOUR", 21),
    )
