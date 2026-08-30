from fastapi import APIRouter

from app.config import settings
from app.models import InfoResponse
from app.services.gemini import gemini_available

router = APIRouter()


@router.get("/info", response_model=InfoResponse)
def info() -> InfoResponse:
    capabilities = [
        "public-github-analysis",
        "commit-history",
        "changed-files",
        "diff-statistics",
        "evidence-retrieval",
        "repository-query",
        "evolution-graph",
        "butterfly-effect",
        "archaeologist-notes",
    ]
    if gemini_available():
        capabilities.append("evidence-grounded-ai")
    return InfoResponse(
        name=settings.app_name,
        version=settings.app_version,
        capabilities=capabilities,
        ai_enabled=gemini_available(),
        max_commits=settings.max_commits,
        session_ttl_minutes=settings.session_ttl_seconds // 60,
    )
