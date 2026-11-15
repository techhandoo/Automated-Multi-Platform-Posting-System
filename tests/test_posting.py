"""Pytest suite for the Automated Multi-Platform Posting System."""

from __future__ import annotations

import re
from typing import Callable

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app

EXPECTED_PLATFORMS = {
    "Mastodon",
    "Bluesky",
    "Telegram",
    "GitHub Gist",
    "Dev.to",
    "Telegraph",
}


def _configured_settings() -> Settings:
    """Return a Settings instance with all six platforms configured."""
    return Settings(
        _env_file=None,
        mastodon_instance_url="https://mastodon.social",
        mastodon_access_token="test-mastodon-token",
        bluesky_pds_url="https://bsky.social",
        bluesky_handle="tester.bsky.social",
        bluesky_app_password="test-app-password",
        github_token="test-github-token",
        devto_api_key="test-devto-key",
        telegram_bot_token="123456:test-telegram-token",
        telegram_chat_id="@test_channel",
        telegraph_access_token="test-telegraph-token",
        http_timeout_seconds=5.0,
    )


def _unconfigured_settings() -> Settings:
    """Return a Settings instance with no platform credentials configured."""
    return Settings(
        _env_file=None,
        mastodon_access_token=None,
        bluesky_handle=None,
        bluesky_app_password=None,
        github_token=None,
        devto_api_key=None,
        telegram_bot_token=None,
        telegram_chat_id=None,
        telegraph_access_token=None,
    )


def _default_success_handler(request: httpx.Request) -> httpx.Response:
    """Return mocked success responses for all six platform APIs."""
    url = str(request.url)

    if url == "https://mastodon.social/api/v1/statuses":
        return httpx.Response(
            200,
            json={"url": "https://mastodon.social/@tester/123456789"},
        )
    if url == "https://bsky.social/xrpc/com.atproto.server.createSession":
        return httpx.Response(
            200,
            json={"accessJwt": "mock-jwt-token", "did": "did:plc:mockdid123"},
        )
    if url == "https://bsky.social/xrpc/com.atproto.repo.createRecord":
        return httpx.Response(
            200,
            json={"uri": "at://did:plc:mockdid123/app.bsky.feed.post/3kabc123"},
        )
    if url.startswith("https://api.telegram.org/bot") and url.endswith("/sendMessage"):
        return httpx.Response(
            200,
            json={"ok": True, "result": {"message_id": 42}},
        )
    if url == "https://api.github.com/gists":
        return httpx.Response(
            201,
            json={"html_url": "https://gist.github.com/tester/abcdef123456"},
        )
    if url == "https://dev.to/api/articles":
        return httpx.Response(
            201,
            json={"url": "https://dev.to/tester/automated-post-123"},
        )
    if url == "https://api.telegra.ph/createPage":
        return httpx.Response(
            200,
            json={"ok": True, "result": {"url": "https://telegra.ph/Automated-Post-11-15"}},
        )

    return httpx.Response(404, json={"error": f"Unexpected URL in mock: {url}"})


@pytest.fixture
def make_client(monkeypatch: pytest.MonkeyPatch):
    """Build a TestClient with overridden Settings and mocked httpx.AsyncClient."""
    real_async_client = httpx.AsyncClient

    def _factory(
        settings: Settings,
        handler: Callable[[httpx.Request], httpx.Response] = _default_success_handler,
    ) -> TestClient:
        transport = httpx.MockTransport(handler)

        def _mock_async_client(*args, **kwargs) -> httpx.AsyncClient:
            kwargs.pop("transport", None)
            return real_async_client(transport=transport, *args, **kwargs)

        monkeypatch.setattr("app.services.posting_service.httpx.AsyncClient", _mock_async_client)
        app.dependency_overrides[get_settings] = lambda: settings
        return TestClient(app)

    yield _factory
    app.dependency_overrides.clear()


def test_health_endpoint(make_client) -> None:
    """GET /health returns 200 with status ok."""
    client = make_client(_unconfigured_settings())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_posting_valid_message_single_url(make_client) -> None:
    """POST /posting with a valid message and 1 URL returns 200."""
    client = make_client(_configured_settings())
    response = client.post(
        "/posting",
        json={"message": "Check out our new release! https://example.com/release"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["results"]) == 6


@pytest.mark.parametrize(
    "payload",
    [
        {"message": ""},
        {"message": "   \t\n  "},
        {"message": "a" * 181 + " https://example.com"},
        {"message": "Hello world without any link"},
        {"message": "Two links https://example.com and https://example.org"},
        {"message": "Broken URL http://"},
        {"message": "Broken URL https://"},
        {"message": "Invalid scheme ftp://example.com/file"},
    ],
)
def test_posting_input_validation_errors(make_client, payload: dict) -> None:
    """POST /posting rejects invalid messages with HTTP 422."""
    client = make_client(_configured_settings())
    response = client.post("/posting", json=payload)
    assert response.status_code == 422


def test_all_six_platforms_succeed(make_client) -> None:
    """All 6 configured platforms succeed and return structured metadata."""
    client = make_client(_configured_settings())
    response = client.post(
        "/posting",
        json={"message": "Launching v1.0 today https://example.com/v1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    results = data["results"]
    assert len(results) == 6
    assert {r["platform"] for r in results} == EXPECTED_PLATFORMS

    for result in results:
        assert result["status"] == "success"
        assert result["posted_url"]
        assert result["public_access"] is True
        assert re.match(r"^\d{4}-\d{2}-\d{2}$", result["date"])
        assert re.match(r"^\d{2}:\d{2}:\d{2}$", result["time"])
        assert result["error"] is None


def test_partial_failure_http_401(make_client) -> None:
    """When one platform returns HTTP 401, the other 5 succeed and overall success is True."""

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "https://mastodon.social/api/v1/statuses":
            return httpx.Response(401, json={"error": "The access token is invalid"})
        return _default_success_handler(request)

    client = make_client(_configured_settings(), handler=handler)
    response = client.post(
        "/posting",
        json={"message": "Partial failure test https://example.com/test"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    by_platform = {r["platform"]: r for r in data["results"]}
    assert len(by_platform) == 6
    assert by_platform["Mastodon"]["status"] == "failed"
    assert by_platform["Mastodon"]["posted_url"] is None
    assert "401" in by_platform["Mastodon"]["error"]

    for name in EXPECTED_PLATFORMS - {"Mastodon"}:
        assert by_platform[name]["status"] == "success"
        assert by_platform[name]["posted_url"]


def test_partial_failure_timeout(make_client) -> None:
    """When one platform times out, the other 5 succeed and overall success is True."""

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "https://api.github.com/gists":
            raise httpx.ReadTimeout("Request timed out", request=request)
        return _default_success_handler(request)

    client = make_client(_configured_settings(), handler=handler)
    response = client.post(
        "/posting",
        json={"message": "Timeout test https://example.com/timeout"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    by_platform = {r["platform"]: r for r in data["results"]}
    assert len(by_platform) == 6
    assert by_platform["GitHub Gist"]["status"] == "failed"
    assert by_platform["GitHub Gist"]["posted_url"] is None
    assert by_platform["GitHub Gist"]["error"]

    for name in EXPECTED_PLATFORMS - {"GitHub Gist"}:
        assert by_platform[name]["status"] == "success"


def test_all_platforms_unconfigured(make_client) -> None:
    """When no platforms are configured, all 6 fail with error details and success is False."""
    client = make_client(_unconfigured_settings())
    response = client.post(
        "/posting",
        json={"message": "No creds test https://example.com/nocreds"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False

    results = data["results"]
    assert len(results) == 6
    assert {r["platform"] for r in results} == EXPECTED_PLATFORMS
    for result in results:
        assert result["status"] == "failed"
        assert result["posted_url"] is None
        assert result["error"]


def test_all_platforms_fail_on_api_errors(make_client) -> None:
    """When all 6 configured platforms fail, success is False and all 6 report errors."""

    def failing_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "Internal Server Error"})

    client = make_client(_configured_settings(), handler=failing_handler)
    response = client.post(
        "/posting",
        json={"message": "All fail test https://example.com/fail"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False

    results = data["results"]
    assert len(results) == 6
    for result in results:
        assert result["status"] == "failed"
        assert result["posted_url"] is None
        assert result["error"]
