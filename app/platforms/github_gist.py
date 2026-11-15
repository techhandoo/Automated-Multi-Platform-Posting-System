"""GitHub Gist platform publisher."""

import httpx

from app.platforms.base import BasePlatform
from app.schemas import PlatformResult


class GitHubGistPlatform(BasePlatform):
    """Publish posts as public GitHub Gists."""

    name: str = "GitHub Gist"
    _endpoint: str = "https://api.github.com/gists"

    def is_configured(self) -> bool:
        """Return True when a GitHub personal access token is configured."""
        return bool(self.settings.github_token and self.settings.github_token.strip())

    async def _publish(self, message: str, client: httpx.AsyncClient) -> PlatformResult:
        """Create a public GitHub Gist containing the message."""
        headers = {
            "Authorization": f"Bearer {self.settings.github_token}",
            "Accept": "application/vnd.github+json",
        }
        payload = {
            "description": "Automated Multi-Platform Post",
            "public": True,
            "files": {
                "post.md": {
                    "content": message,
                }
            },
        }

        response = await client.post(self._endpoint, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        posted_url = data.get("html_url")
        if not posted_url:
            return self._failure("GitHub Gist API response missing html_url")

        return self._success(posted_url=posted_url, public_access=True)
