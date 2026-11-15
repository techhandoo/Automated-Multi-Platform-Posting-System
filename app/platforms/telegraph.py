"""Telegraph platform publisher."""

import httpx

from app.platforms.base import BasePlatform
from app.schemas import PlatformResult


def _derive_title(message: str, max_length: int = 80) -> str:
    """Derive a concise single-line page title from the post message."""
    normalized = " ".join(message.split())
    if not normalized:
        return "Automated Post"
    if len(normalized) <= max_length:
        return normalized
    return normalized[: max_length - 3].rstrip() + "..."


class TelegraphPlatform(BasePlatform):
    """Publish posts as Telegraph pages."""

    name: str = "Telegraph"
    _endpoint: str = "https://api.telegra.ph/createPage"

    def is_configured(self) -> bool:
        """Return True when a Telegraph access token is configured."""
        return bool(
            self.settings.telegraph_access_token
            and self.settings.telegraph_access_token.strip()
        )

    async def _publish(self, message: str, client: httpx.AsyncClient) -> PlatformResult:
        """Create a public Telegraph page."""
        payload = {
            "access_token": self.settings.telegraph_access_token,
            "title": _derive_title(message),
            "content": [{"tag": "p", "children": [message]}],
            "return_content": False,
        }

        response = await client.post(self._endpoint, json=payload)
        response.raise_for_status()
        data = response.json()

        if data.get("ok") is not True:
            return self._failure(data.get("error", "Telegraph API error"))

        posted_url = data.get("result", {}).get("url")
        if not posted_url:
            return self._failure("Telegraph API response missing result.url")

        return self._success(posted_url=posted_url, public_access=True)
