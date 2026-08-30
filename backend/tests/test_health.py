from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "code-archaeologist-api"}


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
