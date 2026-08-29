"""Evidence-grounded Gemini investigation. Falls back cleanly when unavailable."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import httpx
from dotenv import load_dotenv

from app.config import settings
from app.models import ArchaeologistNote, QueryResponse
from app.services.analysis_store import StoredAnalysis

BACKEND_DIR = Path(__file__).resolve().parents[1]

FALLBACK_MODELS = (
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemini-3.7-flash",
    "gemini-flash-latest",
)

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


def _refresh_env() -> None:
    load_dotenv(BACKEND_DIR / ".env", override=True)


def _api_key() -> str:
    _refresh_env()
    return (
        os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
        or settings.gemini_api_key
        or settings.google_api_key
        or ""
    ).strip()


def _preferred_model() -> str:
    _refresh_env()
    return (os.getenv("GEMINI_MODEL") or settings.gemini_model or FALLBACK_MODELS[0]).strip()


def gemini_available() -> bool:
    return bool(_api_key())


def _models_to_try(preferred: str) -> list[str]:
    ordered = [preferred]
    for model in FALLBACK_MODELS:
        if model not in ordered:
            ordered.append(model)
    return ordered


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


def _call_gemini(system: str, user: str) -> tuple[dict[str, object] | str | None, str | None]:
    key = _api_key()
    if not key:
        return None, "not_configured"
    last_reason = "provider_error"
    configs = [
        {
            "temperature": 0.2,
            "maxOutputTokens": 4096,
            "responseMimeType": "application/json",
            "thinkingConfig": {"thinkingBudget": 0},
        },
        {
            "temperature": 0.2,
            "maxOutputTokens": 4096,
            "responseMimeType": "application/json",
        },
    ]
    for model in _models_to_try(_preferred_model()):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        for generation in configs:
            body = {
                "system_instruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": user}]}],
                "generationConfig": generation,
            }
            try:
                with httpx.Client(timeout=settings.gemini_timeout_seconds) as client:
                    result = client.post(
                        url,
                        headers={
                            "x-goog-api-key": key,
                            "Content-Type": "application/json",
                        },
                        json=body,
                    )
                if result.status_code in {401, 403}:
                    return None, "invalid_key"
                if result.status_code == 404:
                    last_reason = "provider_error"
                    break
                if result.status_code >= 400:
                    last_reason = "provider_error"
                    continue
                data = result.json()
                candidates = data.get("candidates") or []
                if not candidates:
                    last_reason = "provider_error"
                    continue
                parts = (candidates[0].get("content") or {}).get("parts") or []
                text = "".join(str(part.get("text") or "") for part in parts).strip()
                if not text:
                    last_reason = "provider_error"
                    continue
                parsed = _parse_json_object(text)
                return (parsed if parsed is not None else text), None
            except (httpx.HTTPError, ValueError, KeyError):
                last_reason = "provider_error"
                continue
    return None, last_reason


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
    key_present = bool(_api_key())
    base = {
        "intent": retrieved.intent,
        "evidence": retrieved.evidence,
        "retrieval_summary": retrieved.retrieval_summary or retrieved.answer,
        "related_commits": retrieved.related_commits,
        "related_files": retrieved.related_files,
        "ai_available": key_present,
    }
    if not key_present:
        return QueryResponse(
            mode="ai-unavailable",
            answer="",
            ai_used=False,
            unavailable_reason="not_configured",
            **base,
        )

    payload = _evidence_payload(analysis, retrieved)
    user = f"Question:\n{question}\n\nEvidence:\n{json.dumps(payload, ensure_ascii=True)}"
    result, reason = _call_gemini(INVESTIGATE_RULES, user)
    if result is None:
        return QueryResponse(
            mode="ai-unavailable",
            answer="",
            ai_used=False,
            unavailable_reason=reason or "provider_error",
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
    if not _api_key():
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
    result, _reason = _call_gemini(NOTES_RULES, json.dumps(payload, ensure_ascii=True))
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
