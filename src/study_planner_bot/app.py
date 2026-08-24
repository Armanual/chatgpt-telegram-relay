from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel

from study_planner_bot.config import Settings, get_settings
from study_planner_bot.repository.factory import create_repository
from study_planner_bot.security import bearer_value, constant_time_equal
from study_planner_bot.services.reminders import ReminderService
from study_planner_bot.telegram.client import TelegramClient
from study_planner_bot.telegram.handlers import TelegramUpdateHandler
from study_planner_bot.time_utils import now_in


class RelayPayload(BaseModel):
    chat_id: int | None = None
    text: str | None = None
    message: str | None = None
    secret: str | None = None
    parse_mode: str | None = None


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    repo = create_repository(resolved_settings)
    telegram = TelegramClient(resolved_settings)
    handler = TelegramUpdateHandler(repo, telegram, resolved_settings)
    reminders = ReminderService(repo, resolved_settings)

    app = FastAPI(
        title="Telegram Study Planner Bot",
        version="0.1.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    @app.get("/")
    @app.get("/api")
    @app.get("/api/health")
    async def health() -> dict[str, Any]:
        return {
            "ok": True,
            "service": "telegram-study-planner-bot",
            "telegram_configured": resolved_settings.has_telegram_token,
            "database": _database_kind(resolved_settings.database_url),
        }

    @app.post("/api/telegram/webhook")
    async def telegram_webhook(
        request: Request,
        x_telegram_bot_api_secret_token: str | None = Header(default=None),
    ) -> dict[str, Any]:
        if resolved_settings.telegram_webhook_secret and not constant_time_equal(
            x_telegram_bot_api_secret_token, resolved_settings.telegram_webhook_secret
        ):
            raise HTTPException(status_code=401, detail="Invalid Telegram webhook secret")
        update = await request.json()
        return await handler.handle(update)

    @app.api_route("/api/telegram/set-webhook", methods=["GET", "POST"])
    async def set_telegram_webhook(
        request: Request,
        authorization: str | None = Header(default=None),
        x_relay_secret: str | None = Header(default=None),
    ) -> dict[str, Any]:
        provided_secret = x_relay_secret or bearer_value(authorization)
        _require_secret(provided_secret, resolved_settings.relay_secret, "Invalid relay secret")
        webhook_url = str(request.url_for("telegram_webhook"))
        result = await telegram.set_webhook(webhook_url, resolved_settings.telegram_webhook_secret)
        return {"ok": True, "webhook_url": webhook_url, "telegram": result}

    @app.post("/api/relay")
    @app.post("/api/telegram/relay")
    @app.post("/api/notify")
    async def relay(
        payload: RelayPayload,
        authorization: str | None = Header(default=None),
        x_relay_secret: str | None = Header(default=None),
    ) -> dict[str, Any]:
        provided_secret = x_relay_secret or bearer_value(authorization) or payload.secret
        _require_secret(provided_secret, resolved_settings.relay_secret, "Invalid relay secret")
        chat_id = payload.chat_id or resolved_settings.telegram_default_chat_id
        text = payload.text or payload.message
        if not chat_id:
            raise HTTPException(status_code=400, detail="chat_id is required")
        if not text:
            raise HTTPException(status_code=400, detail="text or message is required")
        result = await telegram.send_message(chat_id, text, parse_mode=payload.parse_mode)
        return {"ok": True, "telegram": result}

    @app.api_route("/api/cron/reminders", methods=["GET", "POST"])
    async def cron_reminders(
        authorization: str | None = Header(default=None),
        x_cron_secret: str | None = Header(default=None),
    ) -> dict[str, Any]:
        provided_secret = x_cron_secret or bearer_value(authorization)
        _require_secret(provided_secret, resolved_settings.cron_secret, "Invalid cron secret")
        current_time = now_in(resolved_settings.timezone)
        created_daily = reminders.ensure_daily_reminders(current_time)
        sent = 0
        dry_runs: list[dict[str, Any]] = []
        for reminder in reminders.pending(current_time):
            text, markup = reminders.render(reminder, current_time)
            result = await telegram.send_message(reminder.chat_id, text, reply_markup=markup)
            dry_runs.append(result)
            if reminder.id is not None:
                repo.mark_reminder_sent(reminder.id, current_time)
            sent += 1
        return {"ok": True, "created_daily": created_daily, "sent": sent, "telegram": dry_runs}

    return app


def _require_secret(provided: str | None, expected: str | None, detail: str) -> None:
    if not expected:
        raise HTTPException(status_code=500, detail="Server secret is not configured")
    if not constant_time_equal(provided, expected):
        raise HTTPException(status_code=401, detail=detail)


def _database_kind(database_url: str) -> str:
    if database_url.startswith("sqlite:///"):
        return "sqlite"
    if database_url.startswith(("postgres://", "postgresql://")):
        return "postgres"
    return "unknown"
