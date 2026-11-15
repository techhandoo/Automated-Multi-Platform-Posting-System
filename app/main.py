from fastapi import Depends, FastAPI

from app.config import Settings, get_settings
from app.schemas import PostingRequest, PostingResponse
from app.services.posting_service import PostingService

app = FastAPI(
    title="Automated Multi-Platform Posting System",
    version="1.0.0",
)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/posting", response_model=PostingResponse)
async def create_posting(
    request: PostingRequest,
    settings: Settings = Depends(get_settings),
) -> PostingResponse:
    """Publish a validated message concurrently to all configured platforms."""
    service = PostingService(settings)
    return await service.post(request.message)
