"""Tests for pipeline with mocked components."""

import pytest

from src.config import AppConfig, JiraAuthConfig, RubricConfig
from src.jira_client import JiraIssue
from src.pipeline import FeedbackPipeline


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    jira_config = JiraAuthConfig(
        method="pat",
        base_url="https://test.atlassian.net",
        email="test@example.com",
        api_token="fake_token"
    )

    rubric_config = RubricConfig(
        min_description_words=10,
        require_acceptance_criteria=False
    )

    return AppConfig(
        jira=jira_config,
        jql="project = TEST",
        feedback_mode="comment",
        model="gpt-4o-mini",
        openai_api_key="fake_key",
        rubric=rubric_config
    )


def create_test_issue():
    """Create a test issue."""
    data = {
        "key": "TEST-123",
        "fields": {
            "summary": "Add user login feature",
            "description": "Implement user authentication with email and password. Users should be able to log in and receive appropriate error messages on failure.",
            "labels": ["feature", "authentication"],
            "status": {"name": "To Do"},
            "issuetype": {"name": "Story"},
            "assignee": {"displayName": "Test User"},
            "customfield_10016": 5.0
        }
    }
    return JiraIssue(data)


class TestFeedbackPipeline:
    """Test pipeline functionality (without actual LLM calls)."""

    def test_format_rubric_findings(self, mock_config):
        """Test rubric findings formatting."""
        # Skip actual DSPy setup
        pipeline = FeedbackPipeline.__new__(FeedbackPipeline)
        pipeline.config = mock_config

        from src.rubric import RubricResult

        results = [
            RubricResult("test_rule", 1.0, "Test passed", ""),
            RubricResult("test_rule2", 0.5, "Test failed", "Fix this")
        ]

        formatted = pipeline._format_rubric_findings(results)

        assert "test_rule" in formatted
        assert "Test passed" in formatted
        assert "Fix this" in formatted

    def test_extract_ac(self, mock_config):
        """Test AC extraction from description."""
        pipeline = FeedbackPipeline.__new__(FeedbackPipeline)
        pipeline.config = mock_config

        description = """
        Feature description here.

        Acceptance Criteria:
        - User can log in
        - User sees error message
        """

        ac = pipeline._extract_ac(description)
        assert "Acceptance Criteria" in ac

    def test_parse_numbered_list(self, mock_config):
        """Test parsing numbered lists."""
        pipeline = FeedbackPipeline.__new__(FeedbackPipeline)
        pipeline.config = mock_config

        text = """
        1. First suggestion
        2. Second suggestion
        3. Third suggestion
        """

        items = pipeline._parse_numbered_list(text)

        assert len(items) == 3
        assert "First suggestion" in items[0]
        assert "Second suggestion" in items[1]

    def test_get_score_emoji(self, mock_config):
        """Test emoji selection based on score."""
        pipeline = FeedbackPipeline.__new__(FeedbackPipeline)
        pipeline.config = mock_config

        assert pipeline._get_score_emoji(95) == "🌟"
        assert pipeline._get_score_emoji(85) == "✅"
        assert pipeline._get_score_emoji(75) == "👍"
        assert pipeline._get_score_emoji(65) == "⚠️"
        assert pipeline._get_score_emoji(55) == "🔧"
        assert pipeline._get_score_emoji(45) == "❌"


class TestJiraIssue:
    """Test JiraIssue wrapper."""

    def test_basic_properties(self):
        """Test basic property extraction."""
        issue = create_test_issue()

        assert issue.key == "TEST-123"
        assert "login" in issue.summary.lower()
        assert len(issue.description) > 0
        assert "feature" in issue.labels
        assert issue.estimate == 5.0

    def test_content_hash(self):
        """Test content hashing for change detection."""
        issue1 = create_test_issue()
        hash1 = issue1.content_hash()

        # Modify issue
        issue2 = create_test_issue()
        issue2.fields["summary"] = "Different summary"
        hash2 = issue2.content_hash()

        assert hash1 != hash2

    def test_content_hash_same(self):
        """Test that identical issues have same hash."""
        issue1 = create_test_issue()
        issue2 = create_test_issue()

        assert issue1.content_hash() == issue2.content_hash()

    def test_adf_text_extraction(self):
        """Test ADF (Atlassian Document Format) text extraction."""
        adf_data = {
            "key": "TEST-456",
            "fields": {
                "summary": "Test",
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {"type": "text", "text": "This is "},
                                {"type": "text", "text": "ADF text"}
                            ]
                        }
                    ]
                },
                "labels": []
            }
        }

        issue = JiraIssue(adf_data)
        assert "This is ADF text" in issue.description
