"""API configuration settings."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "Jira Feedback API"
    debug: bool = False

    # Database
    database_url: str = "postgresql://jira_feedback:changeme@localhost:5432/jira_feedback"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Security
    secret_key: str = "change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Encryption key for Jira credentials (Fernet key)
    encryption_key: Optional[str] = None

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # LLM
    openai_api_key: Optional[str] = None
    model: str = "gpt-4o-mini"

    # Telegram
    telegram_bot_token: Optional[str] = None
    telegram_webhook_url: Optional[str] = None

    # Default Jira settings (can be overridden per user)
    jira_base_url: Optional[str] = None
    jira_email: Optional[str] = None
    jira_api_token: Optional[str] = None
    jql: Optional[str] = None

    # Rubric defaults
    min_description_words: int = 20
    require_acceptance_criteria: bool = True
    allowed_labels: Optional[str] = None
    ambiguous_terms: str = "optimize,ASAP,soon,quickly,improve,better,enhance,fix,update"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
