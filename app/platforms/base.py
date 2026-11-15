from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.config import Settings
from app.schemas import PlatformResult


class BasePlatform(ABC):
    """Abstract base class for all publishing platform integrations."""

    name: str

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if all required credentials/settings for this platform are present."""

    @abstractmethod
    async def _publish(self, message: str, client: httpx.AsyncClient) -> PlatformResult:
        """Publish the message to the platform and return a PlatformResult."""

    async def post(self, message: str, client: httpx.AsyncClient) -> PlatformResult:
        """Validate configuration, publish the message, and normalize errors into PlatformResult."""
        if not self.is_configured():
            return self._failure(f"{self.name} is not configured")

        try:
            return await self._publish(message, client)
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text.strip()[:300]
            msg = f"HTTP {exc.response.status_code}"
            if detail:
                msg = f"{msg}: {detail}"
            return self._failure(msg)
        except httpx.RequestError as exc:
            return self._failure(f"Request error: {exc}")
        except Exception as exc:
            return self._failure(str(exc) or exc.__class__.__name__)

    def _success(
        self,
        posted_url: Optional[str],
        public_access: bool = True,
        dt: Optional[datetime] = None,
    ) -> PlatformResult:
        if dt is None:
            now = datetime.now(timezone.utc)
        elif dt.tzinfo is not None:
            now = dt.astimezone(timezone.utc)
        else:
            now = dt

        return PlatformResult(
            platform=self.name,
            status="success",
            posted_url=posted_url,
            public_access=public_access,
            date=now.strftime("%Y-%m-%d"),
            time=now.strftime("%H:%M:%S"),
            error=None,
        )

    def _failure(self, error: str) -> PlatformResult:
        return PlatformResult(
            platform=self.name,
            status="failed",
            posted_url=None,
            public_access=False,
            date=None,
            time=None,
            error=error,
        )
