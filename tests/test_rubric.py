"""Tests for rubric evaluation."""

import pytest

from src.config import RubricConfig
from src.jira_client import JiraIssue
from src.rubric import RubricEvaluator


@pytest.fixture
def rubric_config():
    """Standard rubric configuration."""
    return RubricConfig(
        min_description_words=20,
        require_acceptance_criteria=True,
        ambiguous_terms=["optimize", "ASAP", "soon"]
    )


@pytest.fixture
def rubric_evaluator(rubric_config):
    """Rubric evaluator instance."""
    return RubricEvaluator(rubric_config)


def create_mock_issue(
    summary="Add login feature",
    description="This is a test description with more than twenty words to meet the minimum requirement for testing.",
    labels=None,
    estimate=5.0
):
    """Create a mock Jira issue."""
    if labels is None:
        labels = ["feature"]

    data = {
        "key": "TEST-123",
        "fields": {
            "summary": summary,
            "description": description,
            "labels": labels,
            "status": {"name": "To Do"},
            "issuetype": {"name": "Story"},
            "customfield_10016": estimate  # Story points
        }
    }
    return JiraIssue(data)


class TestRubricEvaluator:
    """Test rubric evaluation logic."""

    def test_title_clarity_good(self, rubric_evaluator):
        """Test that clear titles score well."""
        issue = create_mock_issue(summary="Add user authentication to login page")
        result = rubric_evaluator._check_title_clarity(issue)

        assert result.score == 1.0
        assert result.rule_id == "title_clarity"

    def test_title_clarity_with_filler(self, rubric_evaluator):
        """Test that filler words reduce score."""
        issue = create_mock_issue(summary="Maybe just add some login stuff")
        result = rubric_evaluator._check_title_clarity(issue)

        assert result.score < 1.0
        assert "filler" in result.message.lower()

    def test_description_length_adequate(self, rubric_evaluator):
        """Test description with sufficient words."""
        issue = create_mock_issue()
        result = rubric_evaluator._check_description_length(issue)

        assert result.score == 1.0

    def test_description_length_too_short(self, rubric_evaluator):
        """Test description below minimum words."""
        issue = create_mock_issue(description="Short description.")
        result = rubric_evaluator._check_description_length(issue)

        assert result.score < 1.0
        assert "too short" in result.message.lower()

    def test_description_empty(self, rubric_evaluator):
        """Test empty description."""
        issue = create_mock_issue(description="")
        result = rubric_evaluator._check_description_length(issue)

        assert result.score == 0.0
        assert "empty" in result.message.lower()

    def test_acceptance_criteria_present(self, rubric_evaluator):
        """Test detection of acceptance criteria."""
        description = """
        This feature adds login functionality.

        Acceptance Criteria:
        - User can enter username and password
        - User receives error on invalid credentials
        - User is redirected on successful login
        """
        issue = create_mock_issue(description=description)
        result = rubric_evaluator._check_acceptance_criteria(issue)

        assert result.score == 1.0

    def test_acceptance_criteria_missing(self, rubric_evaluator):
        """Test missing acceptance criteria."""
        issue = create_mock_issue(description="Just a simple description.")
        result = rubric_evaluator._check_acceptance_criteria(issue)

        assert result.score == 0.0
        assert "missing" in result.message.lower()

    def test_ambiguous_terms_detection(self, rubric_evaluator):
        """Test detection of ambiguous terms."""
        issue = create_mock_issue(
            summary="Optimize performance ASAP",
            description="We need to optimize this soon."
        )
        result = rubric_evaluator._check_ambiguous_terms(issue)

        assert result.score < 1.0
        assert "optimize" in result.message.lower()
        assert "asap" in result.message.lower()

    def test_no_ambiguous_terms(self, rubric_evaluator):
        """Test clean issue with no ambiguous terms."""
        issue = create_mock_issue(
            summary="Reduce API response time from 500ms to 200ms",
            description="Implement caching to reduce API response time."
        )
        result = rubric_evaluator._check_ambiguous_terms(issue)

        assert result.score == 1.0

    def test_estimate_present(self, rubric_evaluator):
        """Test that estimate is detected."""
        issue = create_mock_issue(estimate=5.0)
        result = rubric_evaluator._check_estimate_present(issue)

        assert result.score == 1.0
        assert "5.0" in result.message

    def test_estimate_missing(self, rubric_evaluator):
        """Test missing estimate."""
        issue = create_mock_issue(estimate=None)
        result = rubric_evaluator._check_estimate_present(issue)

        assert result.score == 0.5
        assert "no estimate" in result.message.lower()

    def test_calculate_final_score(self, rubric_evaluator):
        """Test final score calculation."""
        issue = create_mock_issue()
        results = rubric_evaluator.evaluate(issue)
        final_score, breakdown = rubric_evaluator.calculate_final_score(results)

        assert 0 <= final_score <= 100
        assert isinstance(breakdown, dict)
        assert len(breakdown) > 0

    def test_labels_allowed(self):
        """Test label validation with allowlist."""
        config = RubricConfig(allowed_labels=["bug", "feature", "enhancement"])
        evaluator = RubricEvaluator(config)

        issue = create_mock_issue(labels=["feature", "enhancement"])
        result = evaluator._check_labels(issue)

        assert result.score == 1.0

    def test_labels_invalid(self):
        """Test invalid labels."""
        config = RubricConfig(allowed_labels=["bug", "feature"])
        evaluator = RubricEvaluator(config)

        issue = create_mock_issue(labels=["invalid-label"])
        result = evaluator._check_labels(issue)

        assert result.score < 1.0
        assert "invalid" in result.message.lower()
