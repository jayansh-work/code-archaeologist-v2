"""In-memory analysis session store. Not durable across process restarts."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

from app.models import AnalysisSummary, CommitEvidence, RepositoryInfo


@dataclass
class StoredAnalysis:
    analysis_id: str
    repository: RepositoryInfo
    summary: AnalysisSummary
    commits: list[CommitEvidence]
    created_at: float = field(default_factory=time.time)


class AnalysisStore:
    def __init__(self, ttl_seconds: int, max_sessions: int) -> None:
        self._ttl = ttl_seconds
        self._max_sessions = max_sessions
        self._items: dict[str, StoredAnalysis] = {}
        self._lock = threading.Lock()

    def put(self, analysis: StoredAnalysis) -> None:
        with self._lock:
            self._purge_unlocked()
            self._items[analysis.analysis_id] = analysis
            self._evict_unlocked()

    def get(self, analysis_id: str) -> StoredAnalysis | None:
        with self._lock:
            self._purge_unlocked()
            return self._items.get(analysis_id)

    def _purge_unlocked(self) -> None:
        now = time.time()
        expired = [
            key
            for key, value in self._items.items()
            if now - value.created_at > self._ttl
        ]
        for key in expired:
            del self._items[key]

    def _evict_unlocked(self) -> None:
        if len(self._items) <= self._max_sessions:
            return
        ordered = sorted(self._items.values(), key=lambda item: item.created_at)
        overflow = len(self._items) - self._max_sessions
        for item in ordered[:overflow]:
            self._items.pop(item.analysis_id, None)
