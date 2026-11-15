# Automated Multi-Platform Posting System

A FastAPI-based backend service that publishes a short message containing a single URL to six social and content platforms concurrently via their official HTTP APIs.

## Overview

- **Single Endpoint Publishing**: `POST /posting` validates the incoming message (non-empty, max 200 characters, containing **exactly one** valid `http`/`https` URL) and dispatches it to all configured platforms in parallel using `httpx.AsyncClient` and `asyncio.gather`.
- **Health Check**: `GET /health` returns service health status.
- **Fault Isolation**: Each platform adapter runs independently; if one platform is unconfigured or fails (e.g., HTTP 401 or timeout), the remaining platforms still execute and report their individual results.
- **Structured Responses**: Returns an overall `success` boolean (`True` if at least one platform succeeds) alongside per-platform `status`, `posted_url`, `public_access`, `date` (UTC `YYYY-MM-DD`), `time` (UTC `HH:MM:SS`), and `error` details.

## Architecture

```text
Automated-Multi-Platform-Posting-System/
├── app/
│   ├── main.py                  # FastAPI application, /posting and /health routes
│   ├── config.py                # Pydantic Settings loading environment variables
│   ├── schemas.py               # Request/response models & URL/length validation
│   ├── services/
│   │   └── posting_service.py   # Concurrent orchestration with asyncio.gather & httpx
│   └── platforms/
│       ├── __init__.py          # Platform registry (get_platforms)
│       ├── base.py              # BasePlatform ABC with error handling & result helpers
│       ├── mastodon.py          # Mastodon status publisher
│       ├── bluesky.py           # Bluesky AT Protocol session + record publisher
│       ├── telegram.py          # Telegram Bot API message publisher
│       ├── github_gist.py       # GitHub Gist publisher
│       ├── devto.py             # Dev.to article publisher
│       └── telegraph.py         # Telegraph page publisher
├── tests/
│   └── test_posting.py          # Pytest suite (FastAPI TestClient + mocked httpx)
├── .env.example                 # Environment variable template
├── requirements.txt             # Python dependencies
└── README.md
```

## Supported Platforms & Official APIs

| Platform | Official API Endpoint | Auth / Configuration | Notes |
| :--- | :--- | :--- | :--- |
| **Mastodon** | `POST {MASTODON_INSTANCE_URL}/api/v1/statuses` | `MASTODON_ACCESS_TOKEN` (Bearer), `MASTODON_INSTANCE_URL` (default `https://mastodon.social`) | Posts a public status and returns `url`. |
| **Bluesky** | `POST {BLUESKY_PDS_URL}/xrpc/com.atproto.server.createSession`<br>`POST {BLUESKY_PDS_URL}/xrpc/com.atproto.repo.createRecord` | `BLUESKY_HANDLE`, `BLUESKY_APP_PASSWORD`, `BLUESKY_PDS_URL` (default `https://bsky.social`) | Creates an ATProto session, attaches UTF-8 byte-offset link facet, and returns `https://bsky.app/profile/{handle}/post/{rkey}`. |
| **Telegram** | `POST https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage` | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Returns `https://t.me/{username}/{message_id}` with `public_access=True` when `TELEGRAM_CHAT_ID` starts with `@`; otherwise `posted_url=None` and `public_access=False`. |
| **GitHub Gist** | `POST https://api.github.com/gists` | `GITHUB_TOKEN` (Bearer) | Creates a public `post.md` gist and returns `html_url`. |
| **Dev.to** | `POST https://dev.to/api/articles` | `DEVTO_API_KEY` (`api-key` header) | Publishes a markdown article with a derived title and returns `url`. |
| **Telegraph** | `POST https://api.telegra.ph/createPage` | `TELEGRAPH_ACCESS_TOKEN` | Creates a Telegraph page and returns `result.url`. |

## Setup Instructions

1. **Clone the repository and navigate into it:**
   ```bash
   cd Automated-Multi-Platform-Posting-System
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   ```
   - **Windows (PowerShell):**
     ```powershell
     .venv\Scripts\Activate.ps1
     ```
   - **macOS / Linux:**
     ```bash
     source .venv/bin/activate
     ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   Copy `.env.example` to `.env` and fill in the credentials for the platforms you want to enable:
   ```bash
   cp .env.example .env
   ```
   Key variables in `.env`:
   - `MASTODON_INSTANCE_URL`, `MASTODON_ACCESS_TOKEN`
   - `BLUESKY_PDS_URL`, `BLUESKY_HANDLE`, `BLUESKY_APP_PASSWORD`
   - `GITHUB_TOKEN`
   - `DEVTO_API_KEY`
   - `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
   - `TELEGRAPH_ACCESS_TOKEN`
   - `HTTP_TIMEOUT_SECONDS` (default: `15.0`)

## Running the Server

Start the FastAPI application with Uvicorn:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 4000
```

- **Swagger UI (Interactive API Docs):** [http://localhost:4000/docs](http://localhost:4000/docs)
- **Health Check:** [http://localhost:4000/health](http://localhost:4000/health)

## Sample Request & Response

### Request (`POST /posting`)

```json
{
  "message": "Check out our new release! https://example.com/release"
}
```

### Response (`200 OK`)

```json
{
  "success": true,
  "results": [
    {
      "platform": "Mastodon",
      "status": "success",
      "posted_url": "https://mastodon.social/@user/123456789",
      "public_access": true,
      "date": "2026-11-15",
      "time": "12:00:00",
      "error": null
    },
    {
      "platform": "Bluesky",
      "status": "success",
      "posted_url": "https://bsky.app/profile/user.bsky.social/post/3kabc123",
      "public_access": true,
      "date": "2026-11-15",
      "time": "12:00:00",
      "error": null
    },
    {
      "platform": "Telegram",
      "status": "success",
      "posted_url": "https://t.me/my_channel/42",
      "public_access": true,
      "date": "2026-11-15",
      "time": "12:00:00",
      "error": null
    },
    {
      "platform": "GitHub Gist",
      "status": "success",
      "posted_url": "https://gist.github.com/user/abcdef123456",
      "public_access": true,
      "date": "2026-11-15",
      "time": "12:00:00",
      "error": null
    },
    {
      "platform": "Dev.to",
      "status": "success",
      "posted_url": "https://dev.to/user/new-release-123",
      "public_access": true,
      "date": "2026-11-15",
      "time": "12:00:00",
      "error": null
    },
    {
      "platform": "Telegraph",
      "status": "success",
      "posted_url": "https://telegra.ph/New-Release-11-15",
      "public_access": true,
      "date": "2026-11-15",
      "time": "12:00:00",
      "error": null
    }
  ]
}
```

## Running Tests

The test suite uses `pytest`, FastAPI's `TestClient`, and mocked `httpx` transports (no real external network calls are made):

```bash
pytest -v
```
