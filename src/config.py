"""Configuration management using Pydantic and environment variables."""

import os
from pathlib import Path
from typing import Literal, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

# Load environment variables
load_dotenv()


class JiraAuthConfig(BaseModel):
    """Jira authentication configuration."""

    method: Literal["pat", "oauth"] = Field(default="pat", description="Authentication method")
    base_url: str = Field(..., description="Jira base URL")

    # PAT authentication
    email: Optional[str] = None
    api_token: Optional[str] = None

    # OAuth authentication
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    oauth_token: Optional[str] = None

    @field_validator("base_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Ensure URL doesn't end with slash."""
        return v.rstrip("/")

    def validate_credentials(self) -> None:
        """Validate that required credentials are present based on auth method."""
        if self.method == "pat":
            if not self.email or not self.api_token:
                raise ValueError("PAT auth requires JIRA_EMAIL and JIRA_API_TOKEN")
        elif self.method == "oauth":
            if not self.client_id or not self.client_secret or not self.oauth_token:
                raise ValueError("OAuth requires JIRA_CLIENT_ID, JIRA_CLIENT_SECRET, and JIRA_TOKEN")


class RubricConfig(BaseModel):
    """Rubric evaluation configuration."""

    min_description_words: int = Field(default=20, description="Minimum words in description")
    require_acceptance_criteria: bool = Field(default=True, description="AC required")
    allowed_labels: Optional[list[str]] = Field(default=None, description="Allowed label values")
    ambiguous_terms: list[str] = Field(
        default_factory=lambda: [
            "optimize", "ASAP", "soon", "quickly", "improve", "better",
            "enhance", "fix", "update", "asap", "urgent"
        ],
        description="Terms that indicate vague requirements"
    )

    @field_validator("allowed_labels", mode="before")
    @classmethod
    def parse_labels(cls, v):
        """Parse comma-separated labels from env var."""
        if isinstance(v, str):
            return [label.strip() for label in v.split(",") if label.strip()]
        return v


class AppConfig(BaseModel):
    """Main application configuration."""

    # Jira settings
    jira: JiraAuthConfig
    jql: str = Field(
        default='project = ABC AND status in ("To Do","In Progress") ORDER BY updated DESC',
        description="JQL query for issues"
    )

    # Feedback settings
    feedback_mode: Literal["comment", "report"] = Field(default="comment")
    cache_db_path: Path = Field(default=Path(".cache/jira_feedback.sqlite"))

    # DSPy / LLM settings
    model: str = Field(default="gpt-4o-mini", description="LLM model to use")
    openai_api_key: Optional[str] = None

    # Rubric
    rubric: RubricConfig = Field(default_factory=RubricConfig)

    # Optional integrations
    slack_webhook_url: Optional[str] = None

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Load configuration from environment variables."""
        # Build Jira auth config
        jira_config = JiraAuthConfig(
            method=os.getenv("AUTH_METHOD", "pat"),
            base_url=os.getenv("JIRA_BASE_URL", ""),
            email=os.getenv("JIRA_EMAIL"),
            api_token=os.getenv("JIRA_API_TOKEN"),
            client_id=os.getenv("JIRA_CLIENT_ID"),
            client_secret=os.getenv("JIRA_CLIENT_SECRET"),
            oauth_token=os.getenv("JIRA_TOKEN"),
        )

        # Build rubric config
        rubric_config = RubricConfig(
            min_description_words=int(os.getenv("MIN_DESCRIPTION_WORDS", "20")),
            require_acceptance_criteria=os.getenv("REQUIRE_ACCEPTANCE_CRITERIA", "true").lower() == "true",
            allowed_labels=os.getenv("ALLOWED_LABELS"),
            ambiguous_terms=os.getenv("AMBIGUOUS_TERMS", "").split(",") if os.getenv("AMBIGUOUS_TERMS") else None,
        )

        config = cls(
            jira=jira_config,
            jql=os.getenv("JQL", 'project = ABC AND status in ("To Do","In Progress") ORDER BY updated DESC'),
            feedback_mode=os.getenv("FEEDBACK_MODE", "comment"),
            cache_db_path=Path(os.getenv("CACHE_DB_PATH", ".cache/jira_feedback.sqlite")),
            model=os.getenv("MODEL", "gpt-4o-mini"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            rubric=rubric_config,
            slack_webhook_url=os.getenv("SLACK_WEBHOOK_URL"),
        )

        # Validate credentials
        config.jira.validate_credentials()

        return config

    def ensure_cache_dir(self) -> None:
        """Ensure cache directory exists."""
        self.cache_db_path.parent.mkdir(parents=True, exist_ok=True)
