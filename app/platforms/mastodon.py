from __future__ import annotations

import httpx

from app.platforms.base import BasePlatform
from app.schemas import PlatformResult


class MastodonPlatform(BasePlatform):
    """Mastodon status publishing integration."""

    name = "Mastodon"

    def is_configured(self) -> bool:
        return bool(
            (self.settings.mastodon_instance_url or "").strip()
            and (self.settings.mastodon_access_token or "").strip()
        )

    async def _publish(self, message: str, client: httpx.AsyncClient) -> PlatformResult:
        instance_url = (self.settings.mastodon_instance_url or "").strip().rstrip("/")
        token = (self.settings.mastodon_access_token or "").strip()
        endpoint = f"{instance_url}/api/v1/statuses"

        response = await client.post(
            endpoint,
            headers={"Authorization": f"Bearer {token}"},
            json={"status": message, "visibility": "public"},
        )
        response.raise_for_status()
        data = response.json()

        posted_url = data.get("url")
        if not posted_url:
            return self._failure("Mastodon API response missing post url")

        return self._success(posted_url=posted_url, public_access=True)
