import asyncio

import httpx

import app.platforms
from app.config import Settings
from app.schemas import PlatformResult, PostingResponse


class PostingService:
    """Orchestrates concurrent posting across all registered platforms."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def post(self, message: str) -> PostingResponse:
        """Post message concurrently to all platforms and aggregate results."""
        platforms = app.platforms.get_platforms(self.settings)

        async with httpx.AsyncClient(timeout=self.settings.http_timeout_seconds) as client:
            raw_results = await asyncio.gather(
                *(platform.post(message, client) for platform in platforms),
                return_exceptions=True,
            )

        results: list[PlatformResult] = []
        for platform, outcome in zip(platforms, raw_results):
            if isinstance(outcome, BaseException):
                results.append(
                    PlatformResult(
                        platform=platform.name,
                        status="failed",
                        error=str(outcome) or type(outcome).__name__,
                    )
                )
            else:
                results.append(outcome)

        success = any(r.status == "success" for r in results)
        return PostingResponse(success=success, results=results)
