from fastapi import APIRouter

from app.exceptions import AnalysisNotFoundError, QueryError
from app.models import QueryRequest, QueryResponse
from app.services.analysis_store import ConversationTurn
from app.services.gemini import investigate
from app.services.query_engine import answer_question
from app.store import store

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
def query(payload: QueryRequest) -> QueryResponse:
    if not payload.question:
        raise QueryError("A question is required.")
    analysis = store.get(payload.analysis_id)
    if analysis is None:
        raise AnalysisNotFoundError()

    focus_hashes = [payload.selected_hash] if payload.selected_hash else []

    retrieved = answer_question(
        analysis,
        payload.question,
        focus_hashes=focus_hashes,
        focus_file=payload.selected_file,
    )
    result = investigate(analysis, payload.question, retrieved)
    store.append_turn(
        payload.analysis_id,
        ConversationTurn(
            question=payload.question,
            answer=result.answer or result.retrieval_summary,
            evidence_hashes=[item.hash for item in result.evidence[:6]],
        ),
    )
    return result
