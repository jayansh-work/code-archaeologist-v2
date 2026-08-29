"""Optional Gemini answers grounded in already-retrieved repository evidence."""

from __future__ import annotations

import json

import httpx

from app.config import settings
from app.models import QueryResponse
from app.services.analysis_store import StoredAnalysis

SYSTEM_RULES = """You are helping a developer investigate Git history for Code Archaeologist.

Rules:
- Answer ONLY from the provided evidence JSON.
- Do not invent commits, files, authors, dates, hashes, or statistics.
- If the evidence is insufficient, say so clearly.
- Git history shows what changed, not why a developer made a decision, unless a commit message states it.
- Prefer phrasing such as "the repository history suggests", "based on the available commit message", and "the analyzed Git history does not establish".
- Keep the answer concise and specific. Mention short hashes when you cite commits.
- Do not claim you cloned or read files beyond this evidence.
"""


def gemini_available() -> bool:
    return settings.gemini_enabled


def _evidence_payload(response: QueryResponse, analysis: StoredAnalysis) -> dict[str, object]:
    return {
        "repository": {
            "owner": analysis.repository.owner,
            "name": analysis.repository.name,
            "url": analysis.repository.url,
        },
        "history_window": analysis.summary.history_window,
        "commits_analyzed": analysis.summary.commits_analyzed,
        "intent": response.intent,
        "deterministic_answer": response.answer,
        "evidence": [
            {
                "hash": item.hash,
                "short_hash": item.short_hash,
                "author": item.author,
                "timestamp": item.timestamp,
                "message": item.message,
                "additions": item.additions,
                "deletions": item.deletions,
                "files": item.files[:20],
            }
            for item in response.evidence[:12]
        ],
    }


def ground_answer(
    analysis: StoredAnalysis,
    question: str,
    deterministic: QueryResponse,
) -> QueryResponse:
    if not settings.gemini_enabled:
        return deterministic
    if not deterministic.evidence and deterministic.intent in {"keyword_search", "file_history", "commit_lookup"}:
        return deterministic

    payload = _evidence_payload(deterministic, analysis)
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent"
    )
    body = {
        "system_instruction": {"parts": [{"text": SYSTEM_RULES}]},
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": (
                            f"Question:\n{question}\n\nEvidence:\n"
                            f"{json.dumps(payload, ensure_ascii=True)}"
                        )
                    }
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 512,
        },
    }
    try:
        with httpx.Client(timeout=settings.gemini_timeout_seconds) as client:
            result = client.post(url, params={"key": settings.gemini_api_key}, json=body)
        if result.status_code >= 400:
            return deterministic
        data = result.json()
        candidates = data.get("candidates") or []
        if not candidates:
            return deterministic
        parts = (candidates[0].get("content") or {}).get("parts") or []
        text = "".join(part.get("text", "") for part in parts).strip()
        if not text:
            return deterministic
        return QueryResponse(
            mode="grounded-ai",
            intent=deterministic.intent,
            answer=text,
            evidence=deterministic.evidence,
            ai_used=True,
        )
    except (httpx.HTTPError, ValueError, KeyError):
        return deterministic
