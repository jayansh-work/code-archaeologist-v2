"""The finding panel must never be blank, whatever the provider does.

`investigate` is allowed to fail in several ways: no key, rejected credentials,
rate limit, HTTP error, unparseable body, or a well-formed body with an empty
answer. In every one of those cases the deterministic retrieval has to survive
to the response, and it must not be labelled as an AI answer.
"""

from __future__ import annotations

import httpx
import pytest

from app.models import AnalysisSummary, CommitEvidence, FileChange, RepositoryInfo
from app.services import ai
from app.services.analysis_store import StoredAnalysis
from app.services.query_engine import answer_question

QUESTION = "Which files changed the most?"
PRIMARY = "openai/gpt-4o-mini"
FALLBACK = "anthropic/claude-3.5-haiku"


def _analysis() -> StoredAnalysis:
    commits = [
        CommitEvidence(
            hash="a" * 40,
            short_hash="aaaaaaa",
            author="Ada",
            author_email="ada@example.com",
            timestamp="2026-08-29T10:00:00+00:00",
            message="Fix authentication validation",
            additions=20,
            deletions=4,
            files=[FileChange(path="src/auth.py", additions=18, deletions=4, change_type="modified")],
        )
    ]
    return StoredAnalysis(
        analysis_id="fallback-session",
        repository=RepositoryInfo(
            owner="octocat",
            name="Hello-World",
            url="https://github.com/octocat/Hello-World",
        ),
        summary=AnalysisSummary(
            commits_analyzed=1,
            contributors_found=1,
            files_changed=1,
            additions=20,
            deletions=4,
            first_commit_at="2026-08-29T10:00:00+00:00",
            last_commit_at="2026-08-29T10:00:00+00:00",
            history_window="Analyzing the latest 30 commits",
        ),
        commits=commits,
    )


def _pin_models(monkeypatch: pytest.MonkeyPatch, fallbacks: list[str] | None = None) -> None:
    monkeypatch.setattr(ai, "_api_key", lambda: "test-key")
    monkeypatch.setattr(ai, "_primary_model", lambda: PRIMARY)
    monkeypatch.setattr(ai, "_configured_fallbacks", lambda: list(fallbacks or []))


def _investigate() -> object:
    analysis = _analysis()
    retrieved = answer_question(analysis, QUESTION)
    return ai.investigate(analysis, QUESTION, retrieved)


def _completion(content: object, status: int = 200) -> httpx.Response:
    return httpx.Response(
        status,
        request=httpx.Request("POST", ai.OPENROUTER_URL),
        json={"choices": [{"message": {"content": content}}]},
    )


def _error(status: int, payload: dict[str, object] | None = None) -> httpx.Response:
    return httpx.Response(
        status,
        request=httpx.Request("POST", ai.OPENROUTER_URL),
        json=payload or {"error": {"message": "failed", "code": status}},
    )


def test_models_to_try_uses_configured_list_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ai, "_configured_fallbacks", lambda: [FALLBACK, FALLBACK])
    models = ai._models_to_try(PRIMARY)
    assert models == [PRIMARY, FALLBACK]


def test_parse_json_inside_fence_and_surrounding_text() -> None:
    fenced = 'Sure.\n```json\n{"answer": "Commit [aaaaaaa] changed src/auth.py.", "confidence": "high", "why": "ok", "follow_ups": ["next"]}\n```\n'
    parsed = ai.parse_structured_response(fenced)
    assert parsed is not None
    assert parsed["answer"] == "Commit [aaaaaaa] changed src/auth.py."

    noisy = 'prefix {"answer": "ok", "confidence": "low", "why": "evidence", "follow_ups": []} trailing'
    parsed = ai.parse_structured_response(noisy)
    assert parsed is not None
    assert parsed["answer"] == "ok"


@pytest.mark.parametrize(
    "reason",
    [
        "not_configured",
        "invalid_credentials",
        "insufficient_credits",
        "model_unavailable",
        "provider_timeout",
        "rate_limited",
        "provider_error",
    ],
)
def test_every_failure_reason_keeps_the_git_explanation(monkeypatch: pytest.MonkeyPatch, reason: str) -> None:
    monkeypatch.setattr(ai, "_api_key", lambda: "" if reason == "not_configured" else "test-key")
    monkeypatch.setattr(ai, "_call_openrouter", lambda system, user: (None, reason))

    result = _investigate()
    assert result.mode == "ai-unavailable"
    assert result.ai_used is False
    assert result.unavailable_reason == reason
    assert result.answer.strip(), "The finding must never be blank"
    assert "src/auth.py" in result.answer
    assert result.why, "The UI needs a reason to show beside the fallback"
    assert result.evidence


def test_empty_model_answer_falls_back_instead_of_blanking(monkeypatch: pytest.MonkeyPatch) -> None:
    _pin_models(monkeypatch)
    monkeypatch.setattr(
        ai,
        "_call_openrouter",
        lambda system, user: ({"answer": "   ", "confidence": "high"}, None),
    )

    result = _investigate()
    assert result.ai_used is False
    assert result.mode == "ai-unavailable"
    assert result.unavailable_reason == "provider_error"
    assert result.answer.strip()


def test_successful_structured_answer_is_marked_as_ai(monkeypatch: pytest.MonkeyPatch) -> None:
    _pin_models(monkeypatch)
    monkeypatch.setattr(
        ai,
        "_call_openrouter",
        lambda system, user: (
            {"answer": "Commit [aaaaaaa] changed src/auth.py.", "confidence": "high", "why": "ok"},
            None,
        ),
    )

    result = _investigate()
    assert result.mode == "grounded-ai"
    assert result.ai_used is True
    assert result.confidence == "high"
    assert "aaaaaaa" in result.answer


def test_rate_limit_is_reported_as_rate_limited(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_post(self, url, **kwargs):  # noqa: ANN001, ANN202
        calls.append(url)
        return httpx.Response(
            429,
            request=httpx.Request("POST", url),
            headers={"retry-after": "0.01"},
            json={"error": {"message": "Rate limit exceeded", "code": 429}},
        )

    _pin_models(monkeypatch)
    monkeypatch.setattr(httpx.Client, "post", fake_post)
    monkeypatch.setattr(ai.time, "sleep", lambda _seconds: None)

    result, reason = ai._call_openrouter("system", "user")
    assert result is None
    assert reason == "rate_limited"
    assert len(calls) == 2


def test_invalid_credentials_short_circuit(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(self, url, **kwargs):  # noqa: ANN001, ANN202
        return _error(403)

    _pin_models(monkeypatch, fallbacks=[FALLBACK])
    monkeypatch.setattr(httpx.Client, "post", fake_post)

    result, reason = ai._call_openrouter("system", "user")
    assert result is None
    assert reason == "invalid_credentials"


def test_401_is_invalid_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    _pin_models(monkeypatch)
    monkeypatch.setattr(httpx.Client, "post", lambda self, url, **kwargs: _error(401))
    result, reason = ai._call_openrouter("system", "user")
    assert reason == "invalid_credentials"


def test_402_is_insufficient_credits(monkeypatch: pytest.MonkeyPatch) -> None:
    _pin_models(monkeypatch)
    monkeypatch.setattr(httpx.Client, "post", lambda self, url, **kwargs: _error(402))
    result, reason = ai._call_openrouter("system", "user")
    assert reason == "insufficient_credits"


def test_unparseable_body_is_a_provider_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(self, url, **kwargs):  # noqa: ANN001, ANN202
        return httpx.Response(200, request=httpx.Request("POST", url), text="not json")

    _pin_models(monkeypatch)
    monkeypatch.setattr(httpx.Client, "post", fake_post)

    result, reason = ai._call_openrouter("system", "user")
    assert result is None
    assert reason == "provider_error"


def test_empty_choices_are_a_provider_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(self, url, **kwargs):  # noqa: ANN001, ANN202
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={"choices": []},
        )

    _pin_models(monkeypatch)
    monkeypatch.setattr(httpx.Client, "post", fake_post)
    result, reason = ai._call_openrouter("system", "user")
    assert result is None
    assert reason == "provider_error"


def test_plain_text_response_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(self, url, **kwargs):  # noqa: ANN001, ANN202
        return _completion("Commit [aaaaaaa] did it.")

    _pin_models(monkeypatch)
    monkeypatch.setattr(httpx.Client, "post", fake_post)

    result, reason = ai._call_openrouter("system", "user")
    assert reason is None
    assert result == "Commit [aaaaaaa] did it."


def test_list_content_parts_are_joined(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(self, url, **kwargs):  # noqa: ANN001, ANN202
        return _completion([{"type": "text", "text": "Commit [aaaaaaa] did it."}])

    _pin_models(monkeypatch)
    monkeypatch.setattr(httpx.Client, "post", fake_post)
    result, reason = ai._call_openrouter("system", "user")
    assert reason is None
    assert result == "Commit [aaaaaaa] did it."


def test_json_inside_markdown_fence_is_parsed(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = '```json\n{"answer": "Commit [aaaaaaa] changed src/auth.py.", "confidence": "medium", "why": "files", "follow_ups": ["next"]}\n```'

    def fake_post(self, url, **kwargs):  # noqa: ANN001, ANN202
        return _completion(payload)

    _pin_models(monkeypatch)
    monkeypatch.setattr(httpx.Client, "post", fake_post)
    result, reason = ai._call_openrouter("system", "user")
    assert reason is None
    assert isinstance(result, dict)
    assert result["answer"] == "Commit [aaaaaaa] changed src/auth.py."


def test_structured_json_in_content_is_parsed(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = '{"answer": "Commit [aaaaaaa] changed src/auth.py.", "confidence": "medium", "why": "files", "follow_ups": ["next"]}'

    def fake_post(self, url, **kwargs):  # noqa: ANN001, ANN202
        return _completion(payload)

    _pin_models(monkeypatch)
    monkeypatch.setattr(httpx.Client, "post", fake_post)
    result, reason = ai._call_openrouter("system", "user")
    assert reason is None
    assert isinstance(result, dict)
    assert result["answer"] == "Commit [aaaaaaa] changed src/auth.py."


def test_retry_delay_parsing() -> None:
    response = httpx.Response(
        429,
        request=httpx.Request("POST", "https://example.test"),
        json={"error": {"metadata": {"retryAfter": "2.389824262"}}},
    )
    assert ai._retry_delay_seconds(response) == pytest.approx(2.389824262)

    header = httpx.Response(
        429,
        request=httpx.Request("POST", "https://example.test"),
        headers={"retry-after": "3"},
        json={},
    )
    assert ai._retry_delay_seconds(header) == pytest.approx(3.0)

    none = httpx.Response(429, request=httpx.Request("POST", "https://example.test"), json={})
    assert ai._retry_delay_seconds(none) is None


def test_429_then_success_uses_the_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []

    def fake_post(self, url, **kwargs):  # noqa: ANN001, ANN202
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(
                429,
                request=httpx.Request("POST", url),
                headers={"retry-after": "0.01"},
                json={"error": {"code": 429}},
            )
        return _completion("Commit [aaaaaaa] did it.")

    _pin_models(monkeypatch)
    monkeypatch.setattr(httpx.Client, "post", fake_post)
    monkeypatch.setattr(ai.time, "sleep", lambda _seconds: None)

    result, reason = ai._call_openrouter("system", "user")
    assert reason is None
    assert result == "Commit [aaaaaaa] did it."
    assert len(calls) == 2


def test_repeated_429_stops_after_one_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []

    def fake_post(self, url, **kwargs):  # noqa: ANN001, ANN202
        calls.append(1)
        return _error(429)

    _pin_models(monkeypatch, fallbacks=[FALLBACK])
    monkeypatch.setattr(httpx.Client, "post", fake_post)
    monkeypatch.setattr(ai.time, "sleep", lambda _seconds: None)

    result, reason = ai._call_openrouter("system", "user")
    assert result is None
    assert reason == "rate_limited"
    assert len(calls) == 2


def test_404_tries_configured_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    models: list[str] = []

    def fake_post(self, url, **kwargs):  # noqa: ANN001, ANN202
        model = kwargs["json"]["model"]
        models.append(model)
        if model == PRIMARY:
            return _error(404)
        return _completion('{"answer": "Commit [aaaaaaa] from fallback.", "confidence": "medium"}')

    _pin_models(monkeypatch, fallbacks=[FALLBACK])
    monkeypatch.setattr(httpx.Client, "post", fake_post)

    result, reason = ai._call_openrouter("system", "user")
    assert reason is None
    assert isinstance(result, dict)
    assert "fallback" in str(result["answer"])
    assert models == [PRIMARY, FALLBACK]


def test_404_on_all_models_is_model_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    _pin_models(monkeypatch, fallbacks=[FALLBACK])
    monkeypatch.setattr(httpx.Client, "post", lambda self, url, **kwargs: _error(404))
    result, reason = ai._call_openrouter("system", "user")
    assert result is None
    assert reason == "model_unavailable"


def test_500_is_provider_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _pin_models(monkeypatch)
    monkeypatch.setattr(httpx.Client, "post", lambda self, url, **kwargs: _error(500))
    result, reason = ai._call_openrouter("system", "user")
    assert reason == "provider_error"


def test_timeout_is_provider_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(self, url, **kwargs):  # noqa: ANN001, ANN202
        raise httpx.TimeoutException("timed out")

    _pin_models(monkeypatch)
    monkeypatch.setattr(httpx.Client, "post", fake_post)
    result, reason = ai._call_openrouter("system", "user")
    assert result is None
    assert reason == "provider_timeout"


def test_network_error_is_provider_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(self, url, **kwargs):  # noqa: ANN001, ANN202
        raise httpx.ConnectError("offline")

    _pin_models(monkeypatch)
    monkeypatch.setattr(httpx.Client, "post", fake_post)
    result, reason = ai._call_openrouter("system", "user")
    assert result is None
    assert reason == "provider_error"


def test_identical_questions_are_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []

    def fake(_system: str, user: str) -> tuple[dict[str, object], None]:
        calls.append(1)
        return {"answer": "Commit [aaaaaaa] changed src/auth.py.", "confidence": "high"}, None

    _pin_models(monkeypatch)
    monkeypatch.setattr(ai, "_call_openrouter", fake)

    first = _investigate()
    second = _investigate()
    assert first.ai_used is True
    assert second.ai_used is True
    assert second.answer == first.answer
    assert len(calls) == 1


def test_cache_does_not_reuse_a_different_file_context(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake(_system: str, user: str) -> tuple[dict[str, object], None]:
        calls.append(user)
        return {"answer": f"Commit [aaaaaaa] for {len(calls)}.", "confidence": "high"}, None

    _pin_models(monkeypatch)
    monkeypatch.setattr(ai, "_call_openrouter", fake)
    analysis = _analysis()
    retrieved = answer_question(analysis, QUESTION)
    ai.investigate(analysis, QUESTION, retrieved, selected_file="src/auth.py")
    ai.investigate(analysis, QUESTION, retrieved, selected_file="README.md")
    assert len(calls) == 2


def test_query_endpoint_survives_429(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    from app.main import app
    from app.store import store

    analysis = _analysis()
    store.put(analysis)
    monkeypatch.setattr(ai, "_api_key", lambda: "test-key")
    monkeypatch.setattr(ai, "_call_openrouter", lambda _system, _user: (None, "rate_limited"))

    client = TestClient(app)
    response = client.post(
        "/query",
        json={"analysis_id": analysis.analysis_id, "question": QUESTION},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["unavailable_reason"] == "rate_limited"
    assert body["ai_used"] is False
    assert body["evidence"]
    assert "src/auth.py" in body["answer"]


def test_attribution_headers_omit_referer_unless_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ai, "_app_name", lambda: "Code Archaeologist")
    monkeypatch.setattr(ai, "_site_url", lambda: "")
    headers = ai._request_headers("test-key")
    assert headers["X-Title"] == "Code Archaeologist"
    assert "HTTP-Referer" not in headers
    monkeypatch.setattr(ai, "_site_url", lambda: "https://example.example")
    headers = ai._request_headers("test-key")
    assert headers["HTTP-Referer"] == "https://example.example"


def test_analyze_route_does_not_import_ai() -> None:
    from pathlib import Path

    source = Path("app/routes/analyze.py").read_text(encoding="utf-8")
    assert "gemini" not in source
    assert "openrouter" not in source
    assert "generate_ai_notes" not in source
    frontend = Path(__file__).resolve().parents[2] / "frontend" / "components" / "InvestigationApp.tsx"
    ui = frontend.read_text(encoding="utf-8")
    assert "fetchAiNotes" not in ui
