"""Analysis session store. Survives API reloads via JSON files; still TTL-bounded."""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from app.models import AnalysisSummary, CommitEvidence, RepositoryInfo


@dataclass
class ConversationTurn:
    question: str
    answer: str
    evidence_hashes: list[str]


@dataclass
class StoredAnalysis:
    analysis_id: str
    repository: RepositoryInfo
    summary: AnalysisSummary
    commits: list[CommitEvidence]
    created_at: float = field(default_factory=time.time)
    turns: list[ConversationTurn] = field(default_factory=list)


def _turn_to_dict(turn: ConversationTurn) -> dict[str, object]:
    return {
        "question": turn.question,
        "answer": turn.answer,
        "evidence_hashes": turn.evidence_hashes,
    }


def _analysis_to_dict(analysis: StoredAnalysis) -> dict[str, object]:
    return {
        "analysis_id": analysis.analysis_id,
        "repository": analysis.repository.model_dump(),
        "summary": analysis.summary.model_dump(),
        "commits": [commit.model_dump() for commit in analysis.commits],
        "created_at": analysis.created_at,
        "turns": [_turn_to_dict(turn) for turn in analysis.turns],
    }


def _analysis_from_dict(data: dict[str, object]) -> StoredAnalysis:
    turns_raw = data.get("turns") or []
    turns: list[ConversationTurn] = []
    if isinstance(turns_raw, list):
        for item in turns_raw:
            if not isinstance(item, dict):
                continue
            turns.append(
                ConversationTurn(
                    question=str(item.get("question") or ""),
                    answer=str(item.get("answer") or ""),
                    evidence_hashes=[str(hash_) for hash_ in item.get("evidence_hashes") or []],
                )
            )
    commits_raw = data.get("commits")
    if not isinstance(commits_raw, list):
        raise TypeError("commits")
    return StoredAnalysis(
        analysis_id=str(data["analysis_id"]),
        repository=RepositoryInfo.model_validate(data["repository"]),
        summary=AnalysisSummary.model_validate(data["summary"]),
        commits=[CommitEvidence.model_validate(item) for item in commits_raw],
        created_at=float(data.get("created_at") or time.time()),
        turns=turns,
    )


class AnalysisStore:
    def __init__(
        self,
        ttl_seconds: int,
        max_sessions: int,
        persist_dir: str | Path | None = None,
    ) -> None:
        self._ttl = ttl_seconds
        self._max_sessions = max_sessions
        self._items: dict[str, StoredAnalysis] = {}
        self._lock = threading.Lock()
        self._dir = Path(persist_dir) if persist_dir else None
        if self._dir is not None:
            self._dir.mkdir(parents=True, exist_ok=True)
            self._load_all()

    def put(self, analysis: StoredAnalysis) -> None:
        with self._lock:
            self._purge_unlocked()
            self._items[analysis.analysis_id] = analysis
            self._evict_unlocked()
            self._persist_unlocked(analysis)

    def get(self, analysis_id: str) -> StoredAnalysis | None:
        with self._lock:
            self._purge_unlocked()
            return self._items.get(analysis_id)

    def append_turn(self, analysis_id: str, turn: ConversationTurn) -> None:
        with self._lock:
            self._purge_unlocked()
            item = self._items.get(analysis_id)
            if item is None:
                return
            item.turns.append(turn)
            item.turns = item.turns[-6:]
            self._persist_unlocked(item)

    def _session_path(self, analysis_id: str) -> Path | None:
        if self._dir is None:
            return None
        safe = "".join(ch for ch in analysis_id if ch.isalnum() or ch in "-_")
        if not safe or safe != analysis_id:
            return None
        return self._dir / f"{safe}.json"

    def _persist_unlocked(self, analysis: StoredAnalysis) -> None:
        path = self._session_path(analysis.analysis_id)
        if path is None:
            return
        tmp = path.with_suffix(".json.tmp")
        try:
            tmp.write_text(
                json.dumps(_analysis_to_dict(analysis), ensure_ascii=True),
                encoding="utf-8",
            )
            tmp.replace(path)
        except OSError:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass

    def _delete_unlocked(self, analysis_id: str) -> None:
        path = self._session_path(analysis_id)
        if path is None:
            return
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass

    def _load_all(self) -> None:
        if self._dir is None:
            return
        for path in self._dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    continue
                analysis = _analysis_from_dict(data)
            except (OSError, ValueError, KeyError, TypeError):
                continue
            self._items[analysis.analysis_id] = analysis
        self._purge_unlocked()
        self._evict_unlocked()

    def _purge_unlocked(self) -> None:
        now = time.time()
        expired = [
            key
            for key, value in self._items.items()
            if now - value.created_at > self._ttl
        ]
        for key in expired:
            del self._items[key]
            self._delete_unlocked(key)

    def _evict_unlocked(self) -> None:
        if len(self._items) <= self._max_sessions:
            return
        ordered = sorted(self._items.values(), key=lambda item: item.created_at)
        overflow = len(self._items) - self._max_sessions
        for item in ordered[:overflow]:
            self._items.pop(item.analysis_id, None)
            self._delete_unlocked(item.analysis_id)
