"""Evidence-grounded AI investigation via OpenRouter. Falls back to Git retrieval."""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from collections import OrderedDict
from pathlib import Path

import httpx
from dotenv import load_dotenv

from app.config import settings
from app.models import ArchaeologistNote, QueryResponse
from app.services.analysis_store import StoredAnalysis

BACKEND_DIR = Path(__file__).resolve().parents[1]
_log = logging.getLogger("code_archaeologist.ai")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

MAX_429_RETRIES = 1
MAX_REASONABLE_429_WAIT = 5.0
DEFAULT_429_WAIT = 0.8
MAX_CACHE_ENTRIES = 48

INVESTIGATE_RULES = """You are Code Archaeologist, a software-history investigation assistant.

Use ONLY the repository evidence supplied in this request when making claims about this repository.

Never invent commits, hashes, file paths, authors, timestamps, additions, deletions, or repository events.

Git history usually shows WHAT changed. It does not necessarily establish WHY. If intent is not supported, say so.

Preferred wording:
- "The analyzed history suggests..."
- "The strongest evidence is..."
- "The available Git evidence does not establish..."

Cite relevant commits as [short_hash]. Only cite hashes present in the supplied evidence.
Write 3-6 plain-English sentences. Never leave "answer" empty.

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
    return (os.getenv("OPENROUTER_API_KEY") or settings.openrouter_api_key or "").strip()


def _primary_model() -> str:
    _refresh_env()
    return (os.getenv("OPENROUTER_MODEL") or settings.openrouter_model or "").strip()


def _configured_fallbacks() -> list[str]:
    _refresh_env()
    raw = (os.getenv("OPENROUTER_FALLBACK_MODELS") or settings.openrouter_fallback_models or "").strip()
    return [item.strip() for item in raw.split(",") if item.strip()]


def _app_name() -> str:
    _refresh_env()
    return (os.getenv("OPENROUTER_APP_NAME") or settings.openrouter_app_name or "Code Archaeologist").strip()


def _site_url() -> str:
    _refresh_env()
    return (os.getenv("OPENROUTER_SITE_URL") or settings.openrouter_site_url or "").strip()


def ai_available() -> bool:
    return bool(_api_key())


openrouter_available = ai_available


def _models_to_try(preferred: str) -> list[str]:
    ordered: list[str] = []
    for model in (preferred, *_configured_fallbacks()):
        if model and model not in ordered:
            ordered.append(model)
    return ordered


def parse_structured_response(text: str) -> dict[str, object] | None:
    raw = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", raw, re.DOTALL)
    if fenced:
        raw = fenced.group(1).strip()
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        try:
            data = json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, dict) else None
    return None


def map_provider_error(status_code: int) -> str:
    if status_code in {401, 403}:
        return "invalid_credentials"
    if status_code == 402:
        return "insufficient_credits"
    if status_code == 404:
        return "model_unavailable"
    if status_code == 408:
        return "provider_timeout"
    if status_code == 429:
        return "rate_limited"
    return "provider_error"


def _retry_delay_seconds(response: httpx.Response) -> float | None:
    header = response.headers.get("retry-after")
    if header:
        try:
            return max(0.0, float(header))
        except ValueError:
            pass
    try:
        details = response.json()
    except ValueError:
        return None
    if not isinstance(details, dict):
        return None
    error = details.get("error") or {}
    if not isinstance(error, dict):
        return None
    metadata = error.get("metadata") or {}
    raw = ""
    if isinstance(metadata, dict):
        raw = str(metadata.get("retryAfter") or "")
    if not raw:
        raw = str(error.get("retryAfter") or "")
    try:
        if raw:
            return max(0.0, float(str(raw).rstrip("s")))
    except ValueError:
        return None
    return None


def _429_wait_seconds(delay: float | None, retry_index: int, deadline: float) -> float | None:
    if delay is None or delay > MAX_REASONABLE_429_WAIT:
        wait = min(DEFAULT_429_WAIT * (2**retry_index), MAX_REASONABLE_429_WAIT)
    else:
        wait = delay
    remaining = deadline - time.monotonic() - 2
    if remaining <= 0.2:
        return None
    return max(0.0, min(wait, remaining))


def _message_text(payload: object) -> str:
    if not isinstance(payload, dict):
        return ""
    choices = payload.get("choices") or []
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    message = first.get("message") or {}
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or ""))
        return "".join(parts).strip()
    if content is None:
        return ""
    return str(content).strip()


def _request_headers(key: str) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "X-Title": _app_name() or "Code Archaeologist",
    }
    site = _site_url()
    if site:
        headers["HTTP-Referer"] = site
    return headers


_call_lock = threading.Lock()
_ai_cache: OrderedDict[str, QueryResponse] = OrderedDict()
_cache_lock = threading.Lock()


def _cache_key(
    analysis_id: str,
    question: str,
    selected_hash: str | None,
    selected_file: str | None,
) -> str:
    question_norm = " ".join(question.lower().split())
    return "\n".join(
        [
            analysis_id,
            question_norm,
            (selected_hash or "").strip().lower(),
            (selected_file or "").strip().lower(),
        ]
    )


def clear_ai_cache() -> None:
    with _cache_lock:
        _ai_cache.clear()


def _get_cached(key: str) -> QueryResponse | None:
    with _cache_lock:
        item = _ai_cache.get(key)
        if item is None:
            return None
        _ai_cache.move_to_end(key)
        return item.model_copy(deep=True)


def _put_cached(key: str, response: QueryResponse) -> None:
    if not response.ai_used or response.mode != "grounded-ai":
        return
    with _cache_lock:
        _ai_cache[key] = response.model_copy(deep=True)
        _ai_cache.move_to_end(key)
        while len(_ai_cache) > MAX_CACHE_ENTRIES:
            _ai_cache.popitem(last=False)


def _call_openrouter(system: str, user: str) -> tuple[dict[str, object] | str | None, str | None]:
    key = _api_key()
    if not key:
        return None, "not_configured"
    preferred = _primary_model()
    models = _models_to_try(preferred)
    if not models:
        return None, "model_unavailable"

    last_reason = "provider_error"
    deadline = time.monotonic() + settings.ai_total_budget_seconds

    for index, model in enumerate(models):
        remaining_budget = deadline - time.monotonic()
        if remaining_budget <= 1:
            last_reason = "provider_timeout"
            break
        if index > 0:
            _log.info("OpenRouter primary model unavailable; trying configured fallback.")
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
            "max_tokens": 2048,
        }
        rate_retries = 0
        while True:
            timeout = min(settings.ai_timeout_seconds, deadline - time.monotonic())
            if timeout <= 1:
                return None, "provider_timeout"
            try:
                with httpx.Client(timeout=timeout) as client:
                    result = client.post(
                        OPENROUTER_URL,
                        headers=_request_headers(key),
                        json=body,
                    )
            except httpx.TimeoutException:
                last_reason = "provider_timeout"
                break
            except httpx.HTTPError:
                last_reason = "provider_error"
                break

            if result.status_code == 429:
                if rate_retries >= MAX_429_RETRIES:
                    _log.info("OpenRouter request rate limited; serving Git fallback.")
                    return None, "rate_limited"
                wait = _429_wait_seconds(_retry_delay_seconds(result), rate_retries, deadline)
                if wait is None:
                    _log.info("OpenRouter request rate limited; serving Git fallback.")
                    return None, "rate_limited"
                rate_retries += 1
                time.sleep(wait)
                continue
            if result.status_code in {401, 403}:
                return None, map_provider_error(result.status_code)
            if result.status_code == 402:
                return None, "insufficient_credits"
            if result.status_code == 404:
                last_reason = "model_unavailable"
                break
            if result.status_code == 408:
                last_reason = "provider_timeout"
                break
            if result.status_code >= 500:
                last_reason = "provider_error"
                break
            if result.status_code >= 400:
                last_reason = map_provider_error(result.status_code)
                break

            try:
                data = result.json()
            except ValueError:
                last_reason = "provider_error"
                break
            if isinstance(data, dict) and data.get("error") and not data.get("choices"):
                error = data.get("error") or {}
                code = error.get("code") if isinstance(error, dict) else result.status_code
                try:
                    last_reason = map_provider_error(int(code))
                except (TypeError, ValueError):
                    last_reason = "provider_error"
                if last_reason in {"invalid_credentials", "insufficient_credits", "rate_limited"}:
                    if last_reason == "rate_limited":
                        _log.info("OpenRouter request rate limited; serving Git fallback.")
                    return None, last_reason
                break
            text = _message_text(data)
            if not text:
                last_reason = "provider_error"
                break
            parsed = parse_structured_response(text)
            return (parsed if parsed is not None else text), None

    if last_reason in {"rate_limited", "provider_timeout", "model_unavailable"}:
        if last_reason == "rate_limited":
            _log.info("OpenRouter request rate limited; serving Git fallback.")
        else:
            _log.info("OpenRouter provider failed; serving deterministic evidence.")
    else:
        _log.info("OpenRouter provider failed; serving deterministic evidence.")
    return None, last_reason


call_openrouter = _call_openrouter


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
        "No AI provider key is configured, so this is the retrieved Git explanation rather than an "
        "AI answer."
    ),
    "invalid_credentials": (
        "The AI provider rejected the configured credentials. The Git evidence below is still available."
    ),
    "invalid_key": (
        "The AI provider rejected the configured credentials. The Git evidence below is still available."
    ),
    "insufficient_credits": (
        "The AI provider reported insufficient credits. The Git evidence below is still available."
    ),
    "model_unavailable": (
        "The configured AI model is unavailable. The Git evidence below is still available."
    ),
    "provider_timeout": (
        "The AI provider timed out. The Git evidence below is still available."
    ),
    "rate_limited": (
        "The AI provider has temporarily reached its request limit. The Git evidence below is still available."
    ),
    "provider_error": (
        "AI explanation is temporarily unavailable. The repository evidence retrieved for this question is shown below."
    ),
}


def investigate(
    analysis: StoredAnalysis,
    question: str,
    retrieved: QueryResponse,
    *,
    selected_hash: str | None = None,
    selected_file: str | None = None,
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

    cache_key = _cache_key(analysis.analysis_id, question, selected_hash, selected_file)
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    with _call_lock:
        cached = _get_cached(cache_key)
        if cached is not None:
            return cached
        if not key_present:
            return unavailable("not_configured")

        payload = _evidence_payload(analysis, retrieved)
        user = f"Question:\n{question}\n\nEvidence:\n{json.dumps(payload, ensure_ascii=True)}"
        result, reason = _call_openrouter(INVESTIGATE_RULES, user)
        if result is None:
            return unavailable(reason or "provider_error")
        if isinstance(result, str):
            response = QueryResponse(
                mode="grounded-ai",
                answer=result,
                ai_used=True,
                confidence="medium",
                why="The model returned an explanation grounded in the retrieved commits.",
                **base,
            )
            _put_cached(cache_key, response)
            return response
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
        response = QueryResponse(
            mode="grounded-ai",
            answer=answer,
            ai_used=True,
            confidence=confidence,
            why=str(result.get("why") or "").strip() or None,
            follow_ups=follow_ups,
            **base,
        )
        _put_cached(cache_key, response)
        return response


def generate_ai_notes(analysis: StoredAnalysis) -> list[ArchaeologistNote]:
    """Optional AI notes. The UI does not call this after analysis."""
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
    with _call_lock:
        result, _reason = _call_openrouter(NOTES_RULES, json.dumps(payload, ensure_ascii=True))
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
