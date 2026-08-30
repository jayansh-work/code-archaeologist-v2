"""Block accidental live Gemini calls from the test suite.

Tests that replace `httpx.Client.post` themselves (the 429 / key / parse
cases) override this wrapper. Everything else, including TestClient /query
against a real `.env` key, must not consume quota.
"""

from __future__ import annotations

import httpx
import pytest

from app.services import gemini


@pytest.fixture(autouse=True)
def _no_live_gemini_and_fresh_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    gemini.clear_ai_cache()
    real_post = httpx.Client.post

    def guarded(self: httpx.Client, url: str, **kwargs: object) -> httpx.Response:
        target = str(url)
        if "generativelanguage.googleapis.com" in target:
            return httpx.Response(
                403,
                request=httpx.Request("POST", target),
                json={"error": {"status": "PERMISSION_DENIED"}},
            )
        return real_post(self, url, **kwargs)

    monkeypatch.setattr(httpx.Client, "post", guarded)
