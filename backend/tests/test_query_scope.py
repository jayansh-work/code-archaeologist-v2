"""The main ask records conversation history; inline explanations must not.

Inline "explain this file" / "ask about this butterfly" requests are utility
lookups. If they were recorded, the next main follow-up question would inherit
an unrelated conversation and answer incoherently.
"""

from fastapi.testclient import TestClient

from app.main import app
from app.models import AnalysisSummary, CommitEvidence, FileChange, RepositoryInfo
from app.services.analysis_store import StoredAnalysis
from app.store import store

client = TestClient(app)

ANALYSIS_ID = "scope-test-session"


def _seed() -> StoredAnalysis:
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
        ),
        CommitEvidence(
            hash="b" * 40,
            short_hash="bbbbbbb",
            author="Sam",
            author_email="sam@example.com",
            timestamp="2026-08-28T10:00:00+00:00",
            message="Add login tests",
            additions=40,
            deletions=0,
            files=[FileChange(path="src/auth.py", additions=40, deletions=0, change_type="modified")],
        ),
    ]
    analysis = StoredAnalysis(
        analysis_id=ANALYSIS_ID,
        repository=RepositoryInfo(
            owner="octocat",
            name="Hello-World",
            url="https://github.com/octocat/Hello-World",
        ),
        summary=AnalysisSummary(
            commits_analyzed=len(commits),
            contributors_found=2,
            files_changed=1,
            additions=60,
            deletions=4,
            first_commit_at="2026-08-28T10:00:00+00:00",
            last_commit_at="2026-08-29T10:00:00+00:00",
            history_window="Analyzing the latest 30 commits",
        ),
        commits=commits,
    )
    store.put(analysis)
    return analysis


def test_main_ask_records_conversation_history() -> None:
    _seed()
    response = client.post(
        "/query",
        json={"analysis_id": ANALYSIS_ID, "question": "Which files changed the most?"},
    )
    assert response.status_code == 200
    stored = store.get(ANALYSIS_ID)
    assert stored is not None
    assert [turn.question for turn in stored.turns] == ["Which files changed the most?"]


def test_inline_ask_does_not_record_conversation_history() -> None:
    _seed()
    response = client.post(
        "/query",
        json={
            "analysis_id": ANALYSIS_ID,
            "question": "Explain the file src/auth.py.",
            "selected_file": "src/auth.py",
            "record_history": False,
        },
    )
    assert response.status_code == 200
    stored = store.get(ANALYSIS_ID)
    assert stored is not None
    assert stored.turns == []


def test_record_history_defaults_to_true() -> None:
    _seed()
    client.post("/query", json={"analysis_id": ANALYSIS_ID, "question": "Show recent commits."})
    stored = store.get(ANALYSIS_ID)
    assert stored is not None
    assert len(stored.turns) == 1


def test_explicit_commit_context_focuses_that_commit() -> None:
    _seed()
    response = client.post(
        "/query",
        json={
            "analysis_id": ANALYSIS_ID,
            "question": "What is the butterfly effect of this change?",
            "selected_hash": "b" * 40,
            "record_history": False,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "butterfly"
    assert body["evidence"][0]["short_hash"] == "bbbbbbb"


def test_unknown_analysis_id_is_a_useful_error() -> None:
    response = client.post(
        "/query",
        json={"analysis_id": "no-such-session-id", "question": "Which files changed the most?"},
    )
    assert response.status_code == 404
    detail = response.json()["detail"].lower()
    assert "analy" in detail
    assert "tmp" not in detail
    assert "traceback" not in detail
