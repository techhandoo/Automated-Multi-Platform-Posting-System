from __future__ import annotations

import httpx

from app.platforms.base import BasePlatform
from app.schemas import PlatformResult


class TelegramPlatform(BasePlatform):
    """Telegram Bot API publishing integration."""

    name = "Telegram"

    def is_configured(self) -> bool:
        return bool(
            (self.settings.telegram_bot_token or "").strip()
            and (self.settings.telegram_chat_id or "").strip()
        )

    async def _publish(self, message: str, client: httpx.AsyncClient) -> PlatformResult:
        token = (self.settings.telegram_bot_token or "").strip()
        chat_id = (self.settings.telegram_chat_id or "").strip()
        endpoint = f"https://api.telegram.org/bot{token}/sendMessage"

        response = await client.post(
            endpoint,
            json={"chat_id": chat_id, "text": message},
        )
        response.raise_for_status()
        data = response.json()

        if not data.get("ok"):
            return self._failure(data.get("description", "Telegram API error"))

        result = data.get("result") or {}
        message_id = result.get("message_id")
        if message_id is None:
            return self._failure("Telegram API response missing message_id")

        if chat_id.startswith("@"):
            username = chat_id.lstrip("@")
            posted_url = f"https://t.me/{username}/{message_id}"
            return self._success(posted_url=posted_url, public_access=True)

        return self._success(posted_url=None, public_access=False)
