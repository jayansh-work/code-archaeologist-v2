from fastapi import APIRouter

from app.config import settings
from app.models import InfoResponse

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
        "archaeologist-notes",
    ]
    if settings.gemini_enabled:
        capabilities.append("evidence-grounded-ai")
    return InfoResponse(
        name=settings.app_name,
        version=settings.app_version,
        capabilities=capabilities,
        ai_enabled=settings.gemini_enabled,
        max_commits=settings.max_commits,
        session_ttl_minutes=settings.session_ttl_seconds // 60,
    )
