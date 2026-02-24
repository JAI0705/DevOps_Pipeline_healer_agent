# config/settings.py

"""
Centralized configuration using Pydantic BaseSettings.

All settings are loaded from environment variables (or .env file).
Access via `get_settings()` to use the cached singleton.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings — loaded from env vars / .env file."""

    # ── Required Secrets ──────────────────────────────────────
    groq_api_key: str
    github_token: str

    # ── LLM Settings ──────────────────────────────────────────
    llm_model: str = "llama-3.3-70b-versatile"
    llm_temperature: float = 0.0

    # ── Workflow Settings ─────────────────────────────────────
    max_retries: int = 3
    retry_delay: int = 5

    # ── GitHub Settings ───────────────────────────────────────
    default_base_branch: str = "main"
    branch_prefix: str = "auto-fix"

    # ── Logging ───────────────────────────────────────────────
    log_level: str = "INFO"
    log_json: bool = False  # Set to True in production for structured JSON logs

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


@lru_cache()
def get_settings() -> Settings:
    """Return a cached Settings instance (singleton)."""
    return Settings()
