"""Evidence-grounded Gemini investigation. Falls back cleanly when unavailable."""

from __future__ import annotations

import json
import os
import re
import time
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
- Write 3-6 plain-English sentences. Never leave "answer" empty.

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


def _retry_delay_seconds(response: httpx.Response) -> float | None:
    """Read the retry hint Gemini returns with a 429, if it is usable."""
    header = response.headers.get("retry-after")
    if header:
        try:
            return max(0.0, float(header))
        except ValueError:
            pass
    try:
        details = (response.json().get("error") or {}).get("details") or []
    except ValueError:
        return None
    for detail in details:
        if not isinstance(detail, dict):
            continue
        raw = str(detail.get("retryDelay") or "")
        match = re.match(r"^([0-9]*\.?[0-9]+)s$", raw)
        if match:
            return max(0.0, float(match.group(1)))
    return None


def _call_gemini(system: str, user: str) -> tuple[dict[str, object] | str | None, str | None]:
    key = _api_key()
    if not key:
        return None, "not_configured"
    last_reason = "provider_error"
    rate_limit_waits = 0
    # Model fallbacks multiply the per-request timeout, so the whole chain runs
    # against one wall-clock budget that stays inside the client timeout.
    deadline = time.monotonic() + settings.gemini_total_budget_seconds
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
        if time.monotonic() >= deadline:
            break
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        for generation in configs:
            remaining = deadline - time.monotonic()
            if remaining <= 1:
                break
            attempt_timeout = min(settings.gemini_timeout_seconds, remaining)
            body = {
                "system_instruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": user}]}],
                "generationConfig": generation,
            }
            try:
                with httpx.Client(timeout=attempt_timeout) as client:
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
                if result.status_code == 429:
                    # Every fallback model shares one per-minute quota, so
                    # walking the chain cannot help. Wait out the delay the API
                    # gives us once, then give up and let the caller show the
                    # retrieved Git explanation.
                    delay = _retry_delay_seconds(result)
                    # Observed free-tier delays run to ~17s, so allow a real
                    # wait while leaving room for the retried request itself.
                    budget = min(20.0, deadline - time.monotonic() - 8)
                    if rate_limit_waits == 0 and delay is not None and delay <= budget:
                        rate_limit_waits += 1
                        time.sleep(delay)
                        continue
                    return None, "rate_limited"
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


UNAVAILABLE_NOTE = {
    "not_configured": (
        "No Gemini key is configured, so this is the retrieved Git explanation rather than an "
        "AI answer."
    ),
    "invalid_key": (
        "Gemini rejected the configured key, so this is the retrieved Git explanation rather "
        "than an AI answer."
    ),
    "rate_limited": (
        "Gemini is rate limited right now, so this is the retrieved Git explanation rather than "
        "an AI answer. Retry in a moment for the AI rewrite."
    ),
    "provider_error": (
        "Gemini did not return a usable answer, so this is the retrieved Git explanation rather "
        "than an AI answer."
    ),
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
    # The deterministic retrieval is always the floor. Whatever happens to the
    # provider, the finding panel must never render an empty answer, and the
    # fallback must never be labelled as an AI answer.
    grounded = (retrieved.answer or retrieved.retrieval_summary or "").strip()

    def unavailable(reason: str) -> QueryResponse:
        return QueryResponse(
            mode="ai-unavailable",
            answer=grounded,
            ai_used=False,
            unavailable_reason=reason,
            why=UNAVAILABLE_NOTE.get(reason, UNAVAILABLE_NOTE["provider_error"]),
            follow_ups=retrieved.follow_ups,
            **base,
        )

    if not key_present:
        return unavailable("not_configured")

    payload = _evidence_payload(analysis, retrieved)
    user = f"Question:\n{question}\n\nEvidence:\n{json.dumps(payload, ensure_ascii=True)}"
    result, reason = _call_gemini(INVESTIGATE_RULES, user)
    if result is None:
        return unavailable(reason or "provider_error")
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
        return unavailable("provider_error")
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
