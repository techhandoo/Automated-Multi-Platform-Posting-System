from __future__ import annotations

from app.config import Settings

from .base import BasePlatform
from .bluesky import BlueskyPlatform
from .devto import DevToPlatform
from .github_gist import GitHubGistPlatform
from .mastodon import MastodonPlatform
from .telegram import TelegramPlatform
from .telegraph import TelegraphPlatform


def get_platforms(settings: Settings) -> list[BasePlatform]:
    """Instantiate and return all supported publishing platforms."""
    return [
        MastodonPlatform(settings),
        BlueskyPlatform(settings),
        TelegramPlatform(settings),
        GitHubGistPlatform(settings),
        DevToPlatform(settings),
        TelegraphPlatform(settings),
    ]


__all__ = [
    "BasePlatform",
    "MastodonPlatform",
    "BlueskyPlatform",
    "TelegramPlatform",
    "GitHubGistPlatform",
    "DevToPlatform",
    "TelegraphPlatform",
    "get_platforms",
]
