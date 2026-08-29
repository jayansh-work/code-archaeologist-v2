from fastapi import APIRouter

from app.exceptions import AnalysisNotFoundError, QueryError
from app.models import QueryRequest, QueryResponse
from app.services.gemini import gemini_available, ground_answer
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
    result = answer_question(analysis, payload.question)
    if gemini_available():
        return ground_answer(analysis, payload.question, result)
    return result
