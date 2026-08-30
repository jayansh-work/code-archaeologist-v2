from fastapi import APIRouter

from app.config import settings
from app.models import HealthResponse
from app.services.gemini import gemini_available

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.service_id,
        version=settings.app_version,
        ai_available=gemini_available(),
    )
