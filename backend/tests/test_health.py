from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "code-archaeologist-api"
    assert body["version"] == "2.0.0"
    assert isinstance(body["ai_available"], bool)


def test_health_never_leaks_the_api_key() -> None:
    blob = client.get("/health").text.lower()
    for token in ("api_key", "aiza", "gemini_api_key", "openrouter_api_key", "sk-or-"):
        assert token not in blob


def test_info_lists_implemented_capabilities() -> None:
    response = client.get("/info")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Code Archaeologist"
    assert body["version"] == "2.0.0"
    for capability in (
        "public-github-analysis",
        "commit-history",
        "changed-files",
        "diff-statistics",
        "evidence-retrieval",
        "repository-query",
        "evolution-graph",
        "butterfly-effect",
        "archaeologist-notes",
    ):
        assert capability in body["capabilities"]
    assert body["max_commits"] == 30
    assert isinstance(body["ai_enabled"], bool)
    assert body["ai_provider"] == "openrouter"


def test_info_never_leaks_the_api_key() -> None:
    blob = client.get("/info").text.lower()
    for token in ("openrouter_api_key", "sk-or-", "authorization"):
        assert token not in blob
