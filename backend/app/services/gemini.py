"""Evidence-grounded Gemini investigation. Falls back cleanly when unavailable."""

from __future__ import annotations

import json
import re

import httpx

from app.config import settings
from app.models import ArchaeologistNote, QueryResponse
from app.services.analysis_store import StoredAnalysis

INVESTIGATE_RULES = """You are Code Archaeologist, investigating Git history for a developer.

Rules:
- Answer ONLY from the provided evidence JSON and conversation context.
- Do not invent commits, files, authors, dates, hashes, or statistics.
- If evidence is insufficient, say the analyzed Git history does not provide enough evidence to answer confidently.
- Git history shows what changed, not why, unless a commit message states it.
- If the question is unrelated to this repository, say Code Archaeologist is investigating the selected repository and cannot answer that from Git history.
- Cite commits inline as [short_hash] using hashes from the evidence.
- Keep the answer concise and specific.

Return JSON only:
{
  "answer": "markdown-free explanation with [short_hash] citations",
  "confidence": "high" | "medium" | "low",
  "why": "one or two sentences on why the evidence supports this",
  "follow_ups": ["short follow-up question", "another follow-up"]
}
"""

NOTES_RULES = """You write brief Archaeologist Notes from Git evidence.

Rules:
- Use only the provided evidence.
- Do not invent facts.
- Be concise. One or two sentences per note.
- Do not claim Git proves developer intent.

Return JSON only:
{
  "notes": [
    {"kind": "pattern", "title": "Potential pattern", "body": "...", "commit_hash": null, "file_path": null}
  ]
}
Maximum 2 notes. Prefer one pattern and one caveat if needed.
"""


def gemini_available() -> bool:
    return settings.gemini_enabled


def _parse_json_object(text: str) -> dict[str, object] | None:
    raw = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if fenced:
        raw = fenced.group(1)
    else:
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            raw = raw[start : end + 1]
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _call_gemini(system: str, user: str) -> dict[str, object] | str | None:
    if not settings.gemini_enabled:
        return None
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent"
    )
    body = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 700,
            "responseMimeType": "application/json",
        },
    }
    try:
        with httpx.Client(timeout=settings.gemini_timeout_seconds) as client:
            result = client.post(url, params={"key": settings.gemini_api_key}, json=body)
        if result.status_code >= 400:
            return None
        data = result.json()
        candidates = data.get("candidates") or []
        if not candidates:
            return None
        parts = (candidates[0].get("content") or {}).get("parts") or []
        text = "".join(part.get("text", "") for part in parts).strip()
        if not text:
            return None
        parsed = _parse_json_object(text)
        return parsed if parsed is not None else text
    except (httpx.HTTPError, ValueError, KeyError):
        return None


def _evidence_payload(analysis: StoredAnalysis, retrieved: QueryResponse) -> dict[str, object]:
    return {
        "repository": {
            "owner": analysis.repository.owner,
            "name": analysis.repository.name,
            "url": analysis.repository.url,
        },
        "history_window": analysis.summary.history_window,
        "summary": analysis.summary.model_dump(),
        "retrieval_intent": retrieved.intent,
        "retrieval_summary": retrieved.retrieval_summary or retrieved.answer,
        "evidence": [
            {
                "hash": item.hash,
                "short_hash": item.short_hash,
                "author": item.author,
                "timestamp": item.timestamp,
                "message": item.message,
                "additions": item.additions,
                "deletions": item.deletions,
                "files": item.files[:16],
            }
            for item in retrieved.evidence[:12]
        ],
        "recent_conversation": [
            {"question": turn.question, "answer": turn.answer[:500]}
            for turn in analysis.turns[-4:]
        ],
    }


def investigate(
    analysis: StoredAnalysis,
    question: str,
    retrieved: QueryResponse,
) -> QueryResponse:
    base = {
        "intent": retrieved.intent,
        "evidence": retrieved.evidence,
        "retrieval_summary": retrieved.retrieval_summary or retrieved.answer,
        "related_commits": retrieved.related_commits,
        "related_files": retrieved.related_files,
        "ai_available": settings.gemini_enabled,
    }
    if not settings.gemini_enabled:
        return QueryResponse(
            mode="ai-unavailable",
            answer="",
            ai_used=False,
            unavailable_reason="not_configured",
            **base,
        )

    payload = _evidence_payload(analysis, retrieved)
    user = f"Question:\n{question}\n\nEvidence:\n{json.dumps(payload, ensure_ascii=True)}"
    result = _call_gemini(INVESTIGATE_RULES, user)
    if result is None:
        return QueryResponse(
            mode="ai-unavailable",
            answer="",
            ai_used=False,
            unavailable_reason="provider_error",
            **base,
        )
    if isinstance(result, str):
        return QueryResponse(
            mode="grounded-ai",
            answer=result,
            ai_used=True,
            confidence="medium",
            why="The model returned an explanation grounded in the retrieved commits.",
            **base,
        )
    answer = str(result.get("answer") or "").strip()
    if not answer:
        return QueryResponse(
            mode="ai-unavailable",
            answer="",
            ai_used=False,
            unavailable_reason="provider_error",
            **base,
        )
    confidence = str(result.get("confidence") or "medium").lower()
    if confidence not in {"high", "medium", "low"}:
        confidence = "medium"
    follow_raw = result.get("follow_ups") or []
    follow_ups = [str(item).strip() for item in follow_raw if str(item).strip()][:4]
    if not follow_ups:
        follow_ups = [
            "Which commit is the strongest evidence?",
            "Explain this finding to someone new to the codebase.",
        ]
    return QueryResponse(
        mode="grounded-ai",
        answer=answer,
        ai_used=True,
        confidence=confidence,
        why=str(result.get("why") or "").strip() or None,
        follow_ups=follow_ups,
        **base,
    )


def generate_ai_notes(analysis: StoredAnalysis) -> list[ArchaeologistNote]:
    if not settings.gemini_enabled:
        return []
    payload = {
        "repository": f"{analysis.repository.owner}/{analysis.repository.name}",
        "commits_analyzed": analysis.summary.commits_analyzed,
        "commits": [
            {
                "short_hash": commit.short_hash,
                "message": commit.message,
                "author": commit.author,
                "additions": commit.additions,
                "deletions": commit.deletions,
                "files": [item.path for item in commit.files[:8]],
            }
            for commit in analysis.commits[:12]
        ],
    }
    result = _call_gemini(NOTES_RULES, json.dumps(payload, ensure_ascii=True))
    if not isinstance(result, dict):
        return []
    raw_notes = result.get("notes") or []
    notes: list[ArchaeologistNote] = []
    if not isinstance(raw_notes, list):
        return []
    for item in raw_notes[:2]:
        if not isinstance(item, dict):
            continue
        body = str(item.get("body") or "").strip()
        title = str(item.get("title") or "Potential pattern").strip()
        if not body:
            continue
        notes.append(
            ArchaeologistNote(
                kind=str(item.get("kind") or "pattern"),
                title=title,
                body=body,
                ai_generated=True,
                commit_hash=str(item["commit_hash"]) if item.get("commit_hash") else None,
                file_path=str(item["file_path"]) if item.get("file_path") else None,
            )
        )
    return notes
