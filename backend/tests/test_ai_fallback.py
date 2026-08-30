"""The finding panel must never be blank, whatever the provider does.

`investigate` is allowed to fail in several ways: no key, rejected key, rate
limit, HTTP error, unparseable body, or a well-formed body with an empty
answer. In every one of those cases the deterministic retrieval has to survive
to the response, and it must not be labelled as an AI answer.
"""

import httpx
import pytest

from app.models import AnalysisSummary, CommitEvidence, FileChange, RepositoryInfo
from app.services import gemini
from app.services.analysis_store import StoredAnalysis
from app.services.query_engine import answer_question


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


QUESTION = "Which files changed the most?"


def _investigate() -> object:
    analysis = _analysis()
    retrieved = answer_question(analysis, QUESTION)
    return gemini.investigate(analysis, QUESTION, retrieved)


@pytest.mark.parametrize(
    "reason",
    ["not_configured", "invalid_key", "rate_limited", "provider_error"],
)
def test_every_failure_reason_keeps_the_git_explanation(monkeypatch, reason: str) -> None:
    monkeypatch.setattr(gemini, "_api_key", lambda: "" if reason == "not_configured" else "test-key")
    monkeypatch.setattr(gemini, "_call_gemini", lambda system, user: (None, reason))

    result = _investigate()
    assert result.mode == "ai-unavailable"
    assert result.ai_used is False
    assert result.unavailable_reason == reason
    assert result.answer.strip(), "The finding must never be blank"
    assert "src/auth.py" in result.answer
    assert result.why, "The UI needs a reason to show beside the fallback"
    assert result.evidence


def test_empty_model_answer_falls_back_instead_of_blanking(monkeypatch) -> None:
    monkeypatch.setattr(gemini, "_api_key", lambda: "test-key")
    monkeypatch.setattr(
        gemini,
        "_call_gemini",
        lambda system, user: ({"answer": "   ", "confidence": "high"}, None),
    )

    result = _investigate()
    assert result.ai_used is False
    assert result.mode == "ai-unavailable"
    assert result.unavailable_reason == "provider_error"
    assert result.answer.strip()


def test_successful_answer_is_marked_as_ai(monkeypatch) -> None:
    monkeypatch.setattr(gemini, "_api_key", lambda: "test-key")
    monkeypatch.setattr(
        gemini,
        "_call_gemini",
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


def test_rate_limit_is_reported_as_rate_limited(monkeypatch) -> None:
    """A 429 must not be mislabelled as a generic provider error."""
    calls: list[str] = []

    def fake_post(self, url, **kwargs):  # noqa: ANN001, ANN202
        calls.append(url)
        return httpx.Response(
            429,
            request=httpx.Request("POST", url),
            json={
                "error": {
                    "code": 429,
                    "status": "RESOURCE_EXHAUSTED",
                    "details": [{"retryDelay": "0.01s"}],
                }
            },
        )

    monkeypatch.setattr(gemini, "_api_key", lambda: "test-key")
    monkeypatch.setattr(httpx.Client, "post", fake_post)

    result, reason = gemini._call_gemini("system", "user")
    assert result is None
    assert reason == "rate_limited"
    # Every fallback model shares the quota, so walking the chain cannot help:
    # one attempt plus one honoured retry delay, then stop.
    assert len(calls) == 2


def test_invalid_key_short_circuits(monkeypatch) -> None:
    def fake_post(self, url, **kwargs):  # noqa: ANN001, ANN202
        return httpx.Response(403, request=httpx.Request("POST", url), json={"error": {}})

    monkeypatch.setattr(gemini, "_api_key", lambda: "test-key")
    monkeypatch.setattr(httpx.Client, "post", fake_post)

    result, reason = gemini._call_gemini("system", "user")
    assert result is None
    assert reason == "invalid_key"


def test_unparseable_body_is_a_provider_error(monkeypatch) -> None:
    def fake_post(self, url, **kwargs):  # noqa: ANN001, ANN202
        return httpx.Response(200, request=httpx.Request("POST", url), text="not json")

    monkeypatch.setattr(gemini, "_api_key", lambda: "test-key")
    monkeypatch.setattr(httpx.Client, "post", fake_post)

    result, reason = gemini._call_gemini("system", "user")
    assert result is None
    assert reason == "provider_error"


def test_plain_text_response_is_accepted(monkeypatch) -> None:
    def fake_post(self, url, **kwargs):  # noqa: ANN001, ANN202
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={"candidates": [{"content": {"parts": [{"text": "Commit [aaaaaaa] did it."}]}}]},
        )

    monkeypatch.setattr(gemini, "_api_key", lambda: "test-key")
    monkeypatch.setattr(httpx.Client, "post", fake_post)

    result, reason = gemini._call_gemini("system", "user")
    assert reason is None
    assert result == "Commit [aaaaaaa] did it."


def test_retry_delay_parsing() -> None:
    response = httpx.Response(
        429,
        request=httpx.Request("POST", "https://example.test"),
        json={"error": {"details": [{"retryDelay": "2.389824262s"}]}},
    )
    assert gemini._retry_delay_seconds(response) == pytest.approx(2.389824262)

    header = httpx.Response(
        429,
        request=httpx.Request("POST", "https://example.test"),
        headers={"retry-after": "3"},
        json={},
    )
    assert gemini._retry_delay_seconds(header) == pytest.approx(3.0)

    none = httpx.Response(429, request=httpx.Request("POST", "https://example.test"), json={})
    assert gemini._retry_delay_seconds(none) is None
