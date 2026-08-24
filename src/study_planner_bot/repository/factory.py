from __future__ import annotations

from study_planner_bot.config import Settings, get_settings
from study_planner_bot.repository.base import Repository
from study_planner_bot.repository.postgres import PostgresRepository
from study_planner_bot.repository.sqlite import SQLiteRepository


def create_repository(settings: Settings | None = None) -> Repository:
    resolved = settings or get_settings()
    database_url = resolved.database_url
    if database_url.startswith("sqlite:///"):
        repo = SQLiteRepository(database_url)
        repo.init_schema()
        return repo
    if database_url.startswith(("postgres://", "postgresql://")):
        return PostgresRepository(database_url)
    raise ValueError("DATABASE_URL must start with sqlite:/// or postgresql://")

