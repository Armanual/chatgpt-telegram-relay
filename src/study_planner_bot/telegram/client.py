from __future__ import annotations

import httpx

from study_planner_bot.config import Settings


class TelegramClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.base_url = (
            f"https://api.telegram.org/bot{settings.telegram_bot_token}"
            if settings.has_telegram_token
            else None
        )

    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_markup: dict | None = None,
        parse_mode: str | None = None,
    ) -> dict:
        payload: dict[str, object] = {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        if parse_mode:
            payload["parse_mode"] = parse_mode
        if not self.base_url:
            return {"ok": True, "dry_run": True, "method": "sendMessage", "payload": payload}
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(f"{self.base_url}/sendMessage", json=payload)
            response.raise_for_status()
            return response.json()

    async def answer_callback_query(self, callback_query_id: str, text: str) -> dict:
        payload = {"callback_query_id": callback_query_id, "text": text, "show_alert": False}
        if not self.base_url:
            return {"ok": True, "dry_run": True, "method": "answerCallbackQuery", "payload": payload}
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(f"{self.base_url}/answerCallbackQuery", json=payload)
            response.raise_for_status()
            return response.json()

