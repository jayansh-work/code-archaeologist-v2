from uuid import uuid4

from fastapi import APIRouter

from app.models import AnalyzeRequest, AnalyzeResponse
from app.services.analysis_store import StoredAnalysis
from app.services.git_analyzer import analyze_repository
from app.services.github_url import parse_github_repo_url
from app.store import store

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(payload: AnalyzeRequest) -> AnalyzeResponse:
    owner, name, canonical = parse_github_repo_url(payload.repo_url)
    repository, summary, commits = analyze_repository(owner, name, canonical)
    analysis_id = str(uuid4())
    store.put(
        StoredAnalysis(
            analysis_id=analysis_id,
            repository=repository,
            summary=summary,
            commits=commits,
        )
    )
    return AnalyzeResponse(
        analysis_id=analysis_id,
        repository=repository,
        summary=summary,
        commits=commits,
    )
