"""Tests for configuration module."""

import os
from pathlib import Path

import pytest

from src.config import AppConfig, JiraAuthConfig, RubricConfig


class TestJiraAuthConfig:
    """Tests for JiraAuthConfig."""

    def test_validate_url_strips_trailing_slash(self):
        """Test URL normalization."""
        config = JiraAuthConfig(
            base_url="https://test.atlassian.net/",
            email="test@example.com",
            api_token="token",
        )
        assert config.base_url == "https://test.atlassian.net"

    def test_validate_credentials_pat_success(self):
        """Test valid PAT credentials."""
        config = JiraAuthConfig(
            base_url="https://test.atlassian.net",
            email="test@example.com",
            api_token="token",
            method="pat",
        )
        # Should not raise
        config.validate_credentials()

    def test_validate_credentials_pat_missing_email(self):
        """Test PAT auth with missing email."""
        config = JiraAuthConfig(
            base_url="https://test.atlassian.net",
            api_token="token",
            method="pat",
        )
        with pytest.raises(ValueError, match="JIRA_EMAIL"):
            config.validate_credentials()

    def test_validate_credentials_pat_missing_token(self):
        """Test PAT auth with missing token."""
        config = JiraAuthConfig(
            base_url="https://test.atlassian.net",
            email="test@example.com",
            method="pat",
        )
        with pytest.raises(ValueError, match="JIRA_API_TOKEN"):
            config.validate_credentials()

    def test_validate_credentials_oauth_success(self):
        """Test valid OAuth credentials."""
        config = JiraAuthConfig(
            base_url="https://test.atlassian.net",
            method="oauth",
            client_id="client-id",
            client_secret="client-secret",
            oauth_token="token",
        )
        # Should not raise
        config.validate_credentials()

    def test_validate_credentials_oauth_missing_fields(self):
        """Test OAuth with missing fields."""
        config = JiraAuthConfig(
            base_url="https://test.atlassian.net",
            method="oauth",
            client_id="client-id",
        )
        with pytest.raises(ValueError, match="OAuth"):
            config.validate_credentials()


class TestRubricConfig:
    """Tests for RubricConfig."""

    def test_parse_labels_from_string(self):
        """Test comma-separated labels parsing."""
        config = RubricConfig(allowed_labels="bug, feature, enhancement")
        assert config.allowed_labels == ["bug", "feature", "enhancement"]

    def test_parse_labels_from_list(self):
        """Test list passthrough."""
        config = RubricConfig(allowed_labels=["bug", "feature"])
        assert config.allowed_labels == ["bug", "feature"]

    def test_parse_labels_empty_string(self):
        """Test empty string handling."""
        config = RubricConfig(allowed_labels="")
        assert config.allowed_labels == []

    def test_parse_labels_whitespace(self):
        """Test whitespace handling."""
        config = RubricConfig(allowed_labels=" bug , feature ")
        assert config.allowed_labels == ["bug", "feature"]

    def test_default_ambiguous_terms(self):
        """Test default ambiguous terms list."""
        config = RubricConfig()
        assert len(config.ambiguous_terms) > 0
        assert "optimize" in config.ambiguous_terms
        assert "ASAP" in config.ambiguous_terms


class TestAppConfigFromEnv:
    """Tests for AppConfig.from_env()."""

    def test_from_env_minimal_valid(self, monkeypatch):
        """Test loading with minimal required env vars."""
        monkeypatch.setenv("JIRA_BASE_URL", "https://test.atlassian.net")
        monkeypatch.setenv("JIRA_EMAIL", "test@example.com")
        monkeypatch.setenv("JIRA_API_TOKEN", "test-token")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

        config = AppConfig.from_env()

        assert config.jira.base_url == "https://test.atlassian.net"
        assert config.jira.email == "test@example.com"
        assert config.model == "gpt-4o-mini"  # Default

    def test_from_env_all_options(self, monkeypatch):
        """Test loading with all env vars set."""
        monkeypatch.setenv("JIRA_BASE_URL", "https://custom.atlassian.net")
        monkeypatch.setenv("JIRA_EMAIL", "custom@example.com")
        monkeypatch.setenv("JIRA_API_TOKEN", "custom-token")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-custom")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-custom")
        monkeypatch.setenv("JQL", "project = CUSTOM")
        monkeypatch.setenv("FEEDBACK_MODE", "report")
        monkeypatch.setenv("MODEL", "gpt-4")
        monkeypatch.setenv("MIN_DESCRIPTION_WORDS", "30")
        monkeypatch.setenv("REQUIRE_ACCEPTANCE_CRITERIA", "false")

        config = AppConfig.from_env()

        assert config.jira.base_url == "https://custom.atlassian.net"
        assert config.jql == "project = CUSTOM"
        assert config.feedback_mode == "report"
        assert config.model == "gpt-4"
        assert config.anthropic_api_key == "sk-ant-custom"
        assert config.rubric.min_description_words == 30
        assert config.rubric.require_acceptance_criteria is False

    def test_from_env_type_coercion(self, monkeypatch):
        """Test string to int conversion."""
        monkeypatch.setenv("JIRA_BASE_URL", "https://test.atlassian.net")
        monkeypatch.setenv("JIRA_EMAIL", "test@example.com")
        monkeypatch.setenv("JIRA_API_TOKEN", "test-token")
        monkeypatch.setenv("MIN_DESCRIPTION_WORDS", "25")

        config = AppConfig.from_env()

        assert config.rubric.min_description_words == 25
        assert isinstance(config.rubric.min_description_words, int)

    def test_from_env_boolean_parsing(self, monkeypatch):
        """Test boolean parsing."""
        monkeypatch.setenv("JIRA_BASE_URL", "https://test.atlassian.net")
        monkeypatch.setenv("JIRA_EMAIL", "test@example.com")
        monkeypatch.setenv("JIRA_API_TOKEN", "test-token")
        monkeypatch.setenv("REQUIRE_ACCEPTANCE_CRITERIA", "false")

        config = AppConfig.from_env()

        assert config.rubric.require_acceptance_criteria is False

    def test_from_env_custom_ambiguous_terms(self, monkeypatch):
        """Test custom ambiguous terms parsing."""
        monkeypatch.setenv("JIRA_BASE_URL", "https://test.atlassian.net")
        monkeypatch.setenv("JIRA_EMAIL", "test@example.com")
        monkeypatch.setenv("JIRA_API_TOKEN", "test-token")
        monkeypatch.setenv("AMBIGUOUS_TERMS", "custom, terms, here")

        config = AppConfig.from_env()

        assert config.rubric.ambiguous_terms == ["custom", "terms", "here"]

    def test_from_env_default_ambiguous_terms(self, monkeypatch):
        """Test default ambiguous terms when not set."""
        monkeypatch.setenv("JIRA_BASE_URL", "https://test.atlassian.net")
        monkeypatch.setenv("JIRA_EMAIL", "test@example.com")
        monkeypatch.setenv("JIRA_API_TOKEN", "test-token")
        # Don't set AMBIGUOUS_TERMS

        config = AppConfig.from_env()

        # Should use default from RubricConfig
        assert len(config.rubric.ambiguous_terms) > 0
        assert "optimize" in config.rubric.ambiguous_terms

    def test_from_env_with_custom_env_file(self, tmp_path, monkeypatch):
        """Test loading from custom .env file."""
        env_file = tmp_path / ".env.test"
        env_file.write_text(
            "JIRA_BASE_URL=https://custom.atlassian.net\n"
            "JIRA_EMAIL=custom@test.com\n"
            "JIRA_API_TOKEN=custom-token\n"
        )

        config = AppConfig.from_env(env_file=str(env_file))

        assert config.jira.base_url == "https://custom.atlassian.net"
        assert config.jira.email == "custom@test.com"


class TestAppConfigEnsureCacheDir:
    """Tests for AppConfig.ensure_cache_dir()."""

    def test_ensure_cache_dir_creates_directory(self, tmp_path):
        """Test that cache directory is created."""
        cache_path = tmp_path / "subdir" / "cache.sqlite"
        config = AppConfig(
            jira=JiraAuthConfig(
                base_url="https://test.atlassian.net",
                email="test@example.com",
                api_token="token",
            ),
            cache_db_path=cache_path,
        )

        config.ensure_cache_dir()

        assert cache_path.parent.exists()
