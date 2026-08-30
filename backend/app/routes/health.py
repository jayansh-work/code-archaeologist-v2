from fastapi import APIRouter

from app.config import settings
from app.models import HealthResponse
from app.services.ai import ai_available

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.service_id,
        version=settings.app_version,
        ai_available=ai_available(),
    )
