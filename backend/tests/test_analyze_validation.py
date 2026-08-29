from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_analyze_rejects_malformed_url() -> None:
    response = client.post("/analyze", json={"repo_url": "not-a-url"})
    assert response.status_code == 400
    assert "detail" in response.json()


def test_analyze_rejects_empty() -> None:
    response = client.post("/analyze", json={"repo_url": ""})
    assert response.status_code in (400, 422)


def test_analyze_rejects_non_github() -> None:
    response = client.post("/analyze", json={"repo_url": "https://example.com/owner/repo"})
    assert response.status_code == 400


def test_analyze_rejects_missing_repo_name() -> None:
    response = client.post("/analyze", json={"repo_url": "https://github.com/octocat"})
    assert response.status_code == 400


def test_analyze_missing_body() -> None:
    response = client.post("/analyze", json={})
    assert response.status_code == 422
