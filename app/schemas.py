import ipaddress
import re
from typing import Literal, Optional
from urllib.parse import urlparse

from pydantic import BaseModel, field_validator

_URL_PATTERN = re.compile(r"[a-zA-Z][a-zA-Z0-9+.-]*://\S*")
_DOMAIN_PATTERN = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,63}$"
)
_TRAILING_PUNCT = ".,;:!?)]}\"'"


def _is_valid_http_url(raw_url: str) -> bool:
    """Validate that a candidate string is an http/https URL with a valid domain or IP."""
    cleaned = raw_url.rstrip(_TRAILING_PUNCT)
    try:
        parsed = urlparse(cleaned)
        _ = parsed.port
    except ValueError:
        return False

    if parsed.scheme not in ("http", "https"):
        return False
    if not parsed.netloc or not parsed.hostname:
        return False

    hostname = parsed.hostname
    if _DOMAIN_PATTERN.match(hostname):
        return True

    try:
        ipaddress.ip_address(hostname)
        return True
    except ValueError:
        return False


class PostingRequest(BaseModel):
    """Incoming request payload for posting a message across platforms."""

    message: str

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        """Ensure message is non-empty, <= 200 chars, and contains exactly one valid http/https URL."""
        stripped = value.strip()
        if not stripped:
            raise ValueError("Message must not be empty.")
        if len(stripped) > 200:
            raise ValueError("Message must not exceed 200 characters.")

        matches = _URL_PATTERN.findall(stripped)
        if len(matches) != 1:
            raise ValueError(
                f"Message must contain exactly one valid http/https URL (found {len(matches)})."
            )

        if not _is_valid_http_url(matches[0]):
            raise ValueError("Message contains an invalid URL or domain.")

        return stripped


class PlatformResult(BaseModel):
    """Result of posting a message to a single platform."""

    platform: str
    status: Literal["success", "failed"]
    posted_url: Optional[str] = None
    public_access: bool = False
    date: Optional[str] = None
    time: Optional[str] = None
    error: Optional[str] = None


class PostingResponse(BaseModel):
    """Aggregated response across all configured platforms."""

    success: bool
    results: list[PlatformResult]
