from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables or .env file."""

    mastodon_instance_url: str = "https://mastodon.social"
    mastodon_access_token: Optional[str] = None

    bluesky_pds_url: str = "https://bsky.social"
    bluesky_handle: Optional[str] = None
    bluesky_app_password: Optional[str] = None

    github_token: Optional[str] = None
    devto_api_key: Optional[str] = None

    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None

    telegraph_access_token: Optional[str] = None

    http_timeout_seconds: float = 15.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
