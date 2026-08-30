from fastapi import APIRouter

from app.exceptions import AnalysisNotFoundError
from app.models import NotesRequest, NotesResponse
from app.services.ai import ai_available, generate_ai_notes
from app.store import store

router = APIRouter()


@router.post("/notes", response_model=NotesResponse)
def notes(payload: NotesRequest) -> NotesResponse:
    analysis = store.get(payload.analysis_id)
    if analysis is None:
        raise AnalysisNotFoundError()
    # Kept for optional callers. The investigation UI does not request AI
    # notes after analysis so provider quota stays available for Ask questions.
    if not ai_available():
        return NotesResponse(notes=[], ai_used=False)
    extra = generate_ai_notes(analysis)
    return NotesResponse(notes=extra, ai_used=bool(extra))
