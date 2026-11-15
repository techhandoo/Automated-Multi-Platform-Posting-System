from __future__ import annotations

import re
from datetime import datetime, timezone

import httpx

from app.platforms.base import BasePlatform
from app.schemas import PlatformResult

_URL_PATTERN = re.compile(r"https?://[^\s<>\"'()]+")


def _extract_link_facets(text: str) -> list[dict]:
    """Build ATProto link facets using UTF-8 byte offsets for URLs in text."""
    facets: list[dict] = []
    for match in _URL_PATTERN.finditer(text):
        url = match.group(0).rstrip(".,;:!?")
        if not url:
            continue
        start_char = match.start()
        end_char = start_char + len(url)
        byte_start = len(text[:start_char].encode("utf-8"))
        byte_end = len(text[:end_char].encode("utf-8"))
        facets.append(
            {
                "index": {
                    "byteStart": byte_start,
                    "byteEnd": byte_end,
                },
                "features": [
                    {
                        "$type": "app.bsky.richtext.facet#link",
                        "uri": url,
                    }
                ],
            }
        )
    return facets


class BlueskyPlatform(BasePlatform):
    """Bluesky ATProto publishing integration."""

    name = "Bluesky"

    def is_configured(self) -> bool:
        return bool(
            (self.settings.bluesky_pds_url or "").strip()
            and (self.settings.bluesky_handle or "").strip()
            and (self.settings.bluesky_app_password or "").strip()
        )

    async def _publish(self, message: str, client: httpx.AsyncClient) -> PlatformResult:
        pds_url = (self.settings.bluesky_pds_url or "").strip().rstrip("/")
        handle = (self.settings.bluesky_handle or "").strip().lstrip("@")
        app_password = (self.settings.bluesky_app_password or "").strip()

        session_resp = await client.post(
            f"{pds_url}/xrpc/com.atproto.server.createSession",
            json={"identifier": handle, "password": app_password},
        )
        session_resp.raise_for_status()
        session_data = session_resp.json()

        access_jwt = session_data.get("accessJwt")
        did = session_data.get("did")
        if not access_jwt or not did:
            return self._failure("Bluesky createSession response missing accessJwt or did")

        now = datetime.now(timezone.utc)
        record: dict = {
            "$type": "app.bsky.feed.post",
            "text": message,
            "createdAt": now.isoformat().replace("+00:00", "Z"),
        }
        facets = _extract_link_facets(message)
        if facets:
            record["facets"] = facets

        record_resp = await client.post(
            f"{pds_url}/xrpc/com.atproto.repo.createRecord",
            headers={"Authorization": f"Bearer {access_jwt}"},
            json={
                "repo": did,
                "collection": "app.bsky.feed.post",
                "record": record,
            },
        )
        record_resp.raise_for_status()
        record_data = record_resp.json()

        uri = record_data.get("uri", "")
        rkey = uri.rstrip("/").split("/")[-1] if uri else ""
        if not rkey:
            return self._failure("Bluesky createRecord response missing uri")

        posted_url = f"https://bsky.app/profile/{handle}/post/{rkey}"
        return self._success(posted_url=posted_url, public_access=True, dt=now)
