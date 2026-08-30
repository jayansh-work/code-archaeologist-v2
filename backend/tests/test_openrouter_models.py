from app.config import BACKEND_DIR
from app.services import ai
from app.services.ai import _models_to_try, map_provider_error


def test_dotenv_reloads_from_backend_dir() -> None:
    assert ai.BACKEND_DIR == BACKEND_DIR
    assert (ai.BACKEND_DIR / ".env.example").is_file()



def test_primary_model_stays_first(monkeypatch) -> None:
    monkeypatch.setattr("app.services.ai._configured_fallbacks", lambda: ["anthropic/claude-3.5-haiku"])
    models = _models_to_try("openai/gpt-4o-mini")
    assert models[0] == "openai/gpt-4o-mini"
    assert models[1] == "anthropic/claude-3.5-haiku"
    assert len(models) == 2


def test_map_provider_error() -> None:
    assert map_provider_error(401) == "invalid_credentials"
    assert map_provider_error(403) == "invalid_credentials"
    assert map_provider_error(402) == "insufficient_credits"
    assert map_provider_error(404) == "model_unavailable"
    assert map_provider_error(408) == "provider_timeout"
    assert map_provider_error(429) == "rate_limited"
    assert map_provider_error(500) == "provider_error"
