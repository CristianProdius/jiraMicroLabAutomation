"""Shared test fixtures and utilities."""

from pathlib import Path
from typing import Any, Optional

import pytest

from src.cache import FeedbackCache
from src.config import AppConfig, JiraAuthConfig, RubricConfig
from src.jira_client import JiraIssue


@pytest.fixture
def mock_jira_config() -> JiraAuthConfig:
    """Create a mock Jira auth configuration."""
    return JiraAuthConfig(
        method="pat",
        base_url="https://test.atlassian.net",
        email="test@example.com",
        api_token="test-token",
    )


@pytest.fixture
def mock_rubric_config() -> RubricConfig:
    """Create a standard rubric configuration for testing."""
    return RubricConfig(
        min_description_words=20,
        require_acceptance_criteria=True,
        ambiguous_terms=["optimize", "ASAP", "soon", "quickly"],
    )


@pytest.fixture
def mock_app_config(mock_jira_config: JiraAuthConfig, mock_rubric_config: RubricConfig) -> AppConfig:
    """Create a mock application configuration."""
    return AppConfig(
        jira=mock_jira_config,
        jql='project = TEST AND status = "To Do"',
        feedback_mode="comment",
        cache_db_path=Path(".cache/test_cache.sqlite"),
        model="gpt-4o-mini",
        openai_api_key="test-openai-key",
        rubric=mock_rubric_config,
    )


@pytest.fixture
def temp_cache(tmp_path: Path) -> FeedbackCache:
    """Create a temporary FeedbackCache for testing."""
    cache_path = tmp_path / "test_cache.sqlite"
    cache = FeedbackCache(cache_path)
    yield cache
    cache.close()


@pytest.fixture
def mock_jira_issue_data() -> dict[str, Any]:
    """Return raw Jira issue data for testing."""
    return {
        "key": "TEST-123",
        "fields": {
            "summary": "Add user authentication to login page",
            "description": "This is a test description with more than twenty words to meet the minimum requirement for testing purposes. It includes additional context.",
            "labels": ["feature", "backend"],
            "status": {"name": "To Do"},
            "issuetype": {"name": "Story"},
            "assignee": {"displayName": "Test User", "emailAddress": "test@example.com"},
            "customfield_10016": 5.0,  # Story points
        },
    }


@pytest.fixture
def mock_jira_issue(mock_jira_issue_data: dict[str, Any]) -> JiraIssue:
    """Create a mock JiraIssue for testing."""
    return JiraIssue(mock_jira_issue_data)


def create_jira_issue(
    key: str = "TEST-123",
    summary: str = "Add login feature",
    description: Optional[str] = None,
    labels: Optional[list[str]] = None,
    estimate: Optional[float] = 5.0,
    issue_type: str = "Story",
    status: str = "To Do",
) -> JiraIssue:
    """Factory function to create JiraIssue instances for testing.

    Args:
        key: Issue key (e.g., "TEST-123")
        summary: Issue summary/title
        description: Issue description (defaults to a valid description)
        labels: List of labels
        estimate: Story points estimate
        issue_type: Issue type (Story, Bug, Task, etc.)
        status: Issue status

    Returns:
        JiraIssue instance
    """
    if description is None:
        description = (
            "This is a test description with more than twenty words to meet "
            "the minimum requirement for testing purposes."
        )

    if labels is None:
        labels = ["feature"]

    data = {
        "key": key,
        "fields": {
            "summary": summary,
            "description": description,
            "labels": labels,
            "status": {"name": status},
            "issuetype": {"name": issue_type},
            "customfield_10016": estimate,
        },
    }
    return JiraIssue(data)


def create_feedback(
    issue_key: str = "TEST-123",
    score: float = 75.0,
    emoji: str = "👍",
    overall_assessment: str = "Good issue quality overall.",
    strengths: Optional[list[str]] = None,
    improvements: Optional[list[str]] = None,
    suggestions: Optional[list[str]] = None,
    improved_ac: Optional[str] = None,
) -> "Feedback":
    """Factory function to create Feedback instances for testing.

    Args:
        issue_key: Issue key
        score: Feedback score (0-100)
        emoji: Score emoji
        overall_assessment: Overall assessment text
        strengths: List of strengths
        improvements: List of improvements needed
        suggestions: List of actionable suggestions
        improved_ac: Improved acceptance criteria

    Returns:
        Feedback instance
    """
    from src.pipeline import Feedback

    return Feedback(
        issue_key=issue_key,
        score=score,
        emoji=emoji,
        overall_assessment=overall_assessment,
        strengths=strengths or ["Clear title", "Good description"],
        improvements=improvements or ["Add acceptance criteria"],
        suggestions=suggestions or ["Consider adding more context"],
        rubric_breakdown={
            "title_clarity": {"score": 100.0, "message": "Title is clear"},
            "description_length": {"score": 80.0, "message": "Description adequate"},
        },
        improved_ac=improved_ac,
    )


def create_adf_document(text: str) -> dict[str, Any]:
    """Create an Atlassian Document Format (ADF) structure from plain text.

    Args:
        text: Plain text to convert to ADF

    Returns:
        ADF document structure
    """
    return {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": text}],
            }
        ],
    }
