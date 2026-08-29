from app.config import settings
from app.services.analysis_store import AnalysisStore

store = AnalysisStore(
    ttl_seconds=settings.session_ttl_seconds,
    max_sessions=settings.max_sessions,
    persist_dir=settings.session_dir,
)
