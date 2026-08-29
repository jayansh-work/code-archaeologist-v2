"""Live GitHub analysis tests. These clone a small public repository."""

from fastapi.testclient import TestClient

from app.main import app
from app.store import store

client = TestClient(app)

HELLO_WORLD = "https://github.com/octocat/Hello-World"


def test_analyze_hello_world_and_query_without_recloning() -> None:
    response = client.post("/analyze", json={"repo_url": HELLO_WORLD})
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["repository"]["owner"] == "octocat"
    assert body["repository"]["name"] == "Hello-World"
    assert body["repository"]["url"] == HELLO_WORLD
    assert body["summary"]["commits_analyzed"] >= 1
    assert body["summary"]["history_window"].startswith("Analyzing the latest")
    assert body["commits"], "Expected real commits from Git history"
    assert body["notes"]
    assert any(note["kind"] == "caveat" for note in body["notes"])

    first = body["commits"][0]
    assert len(first["hash"]) >= 7
    assert first["short_hash"]
    assert first["message"]
    assert first["author"]
    assert first["timestamp"]

    analysis_id = body["analysis_id"]
    stored = store.get(analysis_id)
    assert stored is not None
    stored_hashes = [commit.hash for commit in stored.commits]

    files_query = client.post(
        "/query",
        json={"analysis_id": analysis_id, "question": "Which files changed the most?"},
    )
    assert files_query.status_code == 200
    files_body = files_query.json()
    assert files_body["intent"] == "most_changed_files"
    assert files_body["evidence"]
    assert files_body["retrieval_summary"] or files_body["answer"]
    if not files_body["ai_available"]:
        assert files_body["ai_used"] is False
        assert files_body["mode"] == "ai-unavailable"

    recent = client.post(
        "/query",
        json={"analysis_id": analysis_id, "question": "Show recent commits."},
    )
    assert recent.status_code == 200
    assert recent.json()["evidence"]

    contributors = client.post(
        "/query",
        json={"analysis_id": analysis_id, "question": "Who contributed the most?"},
    )
    assert contributors.status_code == 200
    contributors_body = contributors.json()
    contributors_text = f"{contributors_body['answer']} {contributors_body['retrieval_summary']}".lower()
    assert "analyzed" in contributors_text or contributors_body["evidence"]

    readme = client.post(
        "/query",
        json={"analysis_id": analysis_id, "question": "Find commits mentioning README"},
    )
    assert readme.status_code == 200

    hash_lookup = client.post(
        "/query",
        json={"analysis_id": analysis_id, "question": first["short_hash"]},
    )
    assert hash_lookup.status_code == 200
    lookup_body = hash_lookup.json()
    assert lookup_body["evidence"]
    assert lookup_body["evidence"][0]["hash"] == first["hash"]

    nonsense = client.post(
        "/query",
        json={"analysis_id": analysis_id, "question": "zzzzzxqwerty-no-such-token"},
    )
    assert nonsense.status_code == 200
    nonsense_body = nonsense.json()
    assert nonsense_body["evidence"] == []
    blob = f"{nonsense_body['answer']} {nonsense_body['retrieval_summary']}".lower()
    assert "no matching" in blob or "try a commit" in blob or not nonsense_body["ai_used"]

    still = store.get(analysis_id)
    assert still is not None
    assert [commit.hash for commit in still.commits] == stored_hashes


def test_analyze_git_suffix() -> None:
    response = client.post("/analyze", json={"repo_url": HELLO_WORLD + ".git"})
    assert response.status_code == 200, response.text
    assert response.json()["repository"]["url"] == HELLO_WORLD


def test_analyze_missing_repository() -> None:
    response = client.post(
        "/analyze",
        json={"repo_url": "https://github.com/octocat/this-repo-does-not-exist-ca-v2-xyz"},
    )
    assert response.status_code in (404, 408)
    assert "detail" in response.json()


def test_query_unknown_session() -> None:
    response = client.post(
        "/query",
        json={
            "analysis_id": "00000000-0000-0000-0000-000000000000",
            "question": "Which files changed the most?",
        },
    )
    assert response.status_code == 404
    assert "analyze" in response.json()["detail"].lower()
