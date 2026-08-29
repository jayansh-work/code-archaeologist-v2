from app.services.gemini import _models_to_try


def test_model_fallback_includes_current_flash() -> None:
    models = _models_to_try("gemini-3.5-flash")
    assert models[0] == "gemini-3.5-flash"
    assert "gemini-3.6-flash" in models
    assert "gemini-2.0-flash" not in models
