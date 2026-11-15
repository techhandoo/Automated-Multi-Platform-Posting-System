"""Dev.to platform publisher."""

import httpx

from app.platforms.base import BasePlatform
from app.schemas import PlatformResult


def _derive_title(message: str, max_length: int = 80) -> str:
    """Derive a concise single-line article title from the post message."""
    normalized = " ".join(message.split())
    if not normalized:
        return "Automated Post"
    if len(normalized) <= max_length:
        return normalized
    return normalized[: max_length - 3].rstrip() + "..."


class DevToPlatform(BasePlatform):
    """Publish posts as articles on Dev.to."""

    name: str = "Dev.to"
    _endpoint: str = "https://dev.to/api/articles"

    def is_configured(self) -> bool:
        """Return True when a Dev.to API key is configured."""
        return bool(self.settings.devto_api_key and self.settings.devto_api_key.strip())

    async def _publish(self, message: str, client: httpx.AsyncClient) -> PlatformResult:
        """Create and publish a Dev.to article."""
        headers = {
            "api-key": self.settings.devto_api_key,
        }
        payload = {
            "article": {
                "title": _derive_title(message),
                "body_markdown": message,
                "published": True,
            }
        }

        response = await client.post(self._endpoint, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        posted_url = data.get("url")
        if not posted_url:
            return self._failure("Dev.to API response missing url")

        return self._success(posted_url=posted_url, public_access=True)
