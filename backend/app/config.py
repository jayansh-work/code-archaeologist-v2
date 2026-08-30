from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Code Archaeologist"
    app_version: str = "2.0.0"
    service_id: str = "code-archaeologist-api"

    max_commits: int = 30
    clone_timeout_seconds: int = 60
    git_command_timeout_seconds: int = 25

    session_ttl_seconds: int = 45 * 60
    max_sessions: int = 24
    session_dir: str = "tmp/sessions"

    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-4o-mini"
    openrouter_fallback_models: str = "anthropic/claude-3.5-haiku"
    openrouter_app_name: str = "Code Archaeologist"
    openrouter_site_url: str = ""
    # Per-request timeout, then a ceiling for the whole model-fallback chain so
    # the API always responds before the browser's own query timeout.
    ai_timeout_seconds: int = 20
    ai_total_budget_seconds: int = 40

    @property
    def allowed_origins(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def ai_enabled(self) -> bool:
        return bool(self.openrouter_api_key.strip())


settings = Settings()
