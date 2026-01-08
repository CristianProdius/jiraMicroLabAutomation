"""Tests for feedback_writer module."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.feedback_writer import FeedbackWriter, generate_summary_report
from tests.conftest import create_feedback


class TestFeedbackWriter:
    """Tests for FeedbackWriter class."""

    def test_init_defaults(self):
        """Test default initialization."""
        writer = FeedbackWriter(mode="comment")
        assert writer.mode == "comment"
        assert writer.jira_client is None
        assert writer.slack_webhook is None

    def test_init_with_all_params(self):
        """Test initialization with all parameters."""
        mock_client = MagicMock()
        writer = FeedbackWriter(
            mode="report",
            jira_client=mock_client,
            slack_webhook="https://hooks.slack.com/test",
        )
        assert writer.mode == "report"
        assert writer.jira_client is mock_client
        assert writer.slack_webhook == "https://hooks.slack.com/test"


class TestFeedbackWriterDeliver:
    """Tests for FeedbackWriter.deliver() method."""

    def test_deliver_dry_run_returns_true(self, capsys):
        """Test dry run mode prints feedback and returns True."""
        writer = FeedbackWriter(mode="comment")
        feedback = create_feedback()

        result = writer.deliver(feedback, dry_run=True)

        assert result is True

    def test_deliver_comment_mode_success(self):
        """Test successful comment posting."""
        mock_client = MagicMock()
        mock_client.add_comment.return_value = None
        writer = FeedbackWriter(mode="comment", jira_client=mock_client)
        feedback = create_feedback()

        result = writer.deliver(feedback, dry_run=False)

        assert result is True
        mock_client.add_comment.assert_called_once()
        call_args = mock_client.add_comment.call_args
        assert call_args[0][0] == "TEST-123"

    def test_deliver_comment_mode_no_client(self):
        """Test comment mode without Jira client."""
        writer = FeedbackWriter(mode="comment", jira_client=None)
        feedback = create_feedback()

        result = writer.deliver(feedback, dry_run=False)

        assert result is False

    def test_deliver_comment_mode_api_failure(self):
        """Test comment mode with API failure."""
        from src.exceptions import JiraAPIError

        mock_client = MagicMock()
        mock_client.add_comment.side_effect = JiraAPIError("API Error")
        writer = FeedbackWriter(mode="comment", jira_client=mock_client)
        feedback = create_feedback()

        result = writer.deliver(feedback, dry_run=False)

        assert result is False

    def test_deliver_report_mode_creates_file(self, tmp_path, monkeypatch):
        """Test report mode creates markdown file."""
        # Change to tmp directory for reports
        monkeypatch.chdir(tmp_path)
        writer = FeedbackWriter(mode="report")
        feedback = create_feedback()

        result = writer.deliver(feedback, dry_run=False)

        assert result is True
        reports_dir = tmp_path / "reports"
        assert reports_dir.exists()
        report_files = list(reports_dir.glob("*.md"))
        assert len(report_files) == 1

    def test_deliver_unknown_mode(self):
        """Test unknown feedback mode."""
        writer = FeedbackWriter(mode="unknown")
        feedback = create_feedback()

        result = writer.deliver(feedback, dry_run=False)

        assert result is False


class TestFeedbackWriterFormatting:
    """Tests for feedback formatting."""

    def test_format_as_markdown_basic(self):
        """Test basic markdown formatting."""
        writer = FeedbackWriter(mode="comment")
        feedback = create_feedback(
            issue_key="TEST-456",
            score=85.5,
            emoji="✅",
            overall_assessment="This is a well-written issue.",
        )

        markdown = writer._format_as_markdown(feedback)

        assert "## ✅ Feedback for TEST-456" in markdown
        assert "**Score:** 85.5/100" in markdown
        assert "This is a well-written issue." in markdown

    def test_format_as_markdown_with_strengths(self):
        """Test markdown formatting with strengths."""
        writer = FeedbackWriter(mode="comment")
        feedback = create_feedback(strengths=["Clear title", "Good acceptance criteria"])

        markdown = writer._format_as_markdown(feedback)

        assert "### ✅ Strengths" in markdown
        assert "- Clear title" in markdown
        assert "- Good acceptance criteria" in markdown

    def test_format_as_markdown_with_improvements(self):
        """Test markdown formatting with improvements."""
        writer = FeedbackWriter(mode="comment")
        feedback = create_feedback(improvements=["Add more details", "Include estimates"])

        markdown = writer._format_as_markdown(feedback)

        assert "### 🔧 Areas for Improvement" in markdown
        assert "- Add more details" in markdown
        assert "- Include estimates" in markdown

    def test_format_as_markdown_with_suggestions(self):
        """Test markdown formatting with numbered suggestions."""
        writer = FeedbackWriter(mode="comment")
        feedback = create_feedback(suggestions=["First suggestion", "Second suggestion"])

        markdown = writer._format_as_markdown(feedback)

        assert "### 💡 Actionable Suggestions" in markdown
        assert "1. First suggestion" in markdown
        assert "2. Second suggestion" in markdown

    def test_format_as_markdown_with_improved_ac(self):
        """Test markdown formatting with improved acceptance criteria."""
        writer = FeedbackWriter(mode="comment")
        feedback = create_feedback(improved_ac="Given user is logged in\nWhen they click logout\nThen session ends")

        markdown = writer._format_as_markdown(feedback)

        assert "### 📋 Proposed Acceptance Criteria" in markdown
        assert "Given user is logged in" in markdown

    def test_format_as_markdown_rubric_breakdown(self):
        """Test markdown formatting includes rubric breakdown."""
        writer = FeedbackWriter(mode="comment")
        feedback = create_feedback()

        markdown = writer._format_as_markdown(feedback)

        assert "<details>" in markdown
        assert "Detailed Rubric Breakdown" in markdown
        assert "title_clarity" in markdown

    def test_format_as_markdown_footer(self):
        """Test markdown footer is included."""
        writer = FeedbackWriter(mode="comment")
        feedback = create_feedback()

        markdown = writer._format_as_markdown(feedback)

        assert "Generated by DSPy Jira Feedback" in markdown


class TestFeedbackWriterReportMode:
    """Tests for report mode functionality."""

    def test_append_to_report_creates_directory(self, tmp_path, monkeypatch):
        """Test report mode creates reports directory."""
        monkeypatch.chdir(tmp_path)
        writer = FeedbackWriter(mode="report")
        feedback = create_feedback()

        writer._append_to_report(feedback)

        assert (tmp_path / "reports").exists()

    def test_append_to_report_appends_to_existing(self, tmp_path, monkeypatch):
        """Test appending to existing report file."""
        monkeypatch.chdir(tmp_path)
        writer = FeedbackWriter(mode="report")

        # Create first feedback
        feedback1 = create_feedback(issue_key="TEST-1", score=80.0)
        writer._append_to_report(feedback1)

        # Get the created file
        reports_dir = tmp_path / "reports"
        report_files = list(reports_dir.glob("*.md"))
        assert len(report_files) == 1

        first_content = report_files[0].read_text()
        assert "TEST-1" in first_content

    def test_append_to_report_handles_write_error(self, tmp_path, monkeypatch):
        """Test handling of write errors."""
        monkeypatch.chdir(tmp_path)
        writer = FeedbackWriter(mode="report")
        feedback = create_feedback()

        # Make reports dir read-only to cause error
        reports_dir = tmp_path / "reports"
        reports_dir.mkdir()

        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            result = writer._append_to_report(feedback)

        assert result is False


class TestSlackNotification:
    """Tests for Slack notification functionality."""

    def test_send_slack_no_webhook(self):
        """Test Slack notification without webhook configured."""
        writer = FeedbackWriter(mode="comment", slack_webhook=None)
        feedbacks = [create_feedback()]

        # Should return without error
        writer.send_slack_notification(feedbacks)

    def test_send_slack_empty_feedbacks(self):
        """Test Slack notification with empty feedback list."""
        writer = FeedbackWriter(mode="comment", slack_webhook="https://hooks.slack.com/test")

        # Should return without error
        writer.send_slack_notification([])

    @patch("httpx.post")
    def test_send_slack_success(self, mock_post):
        """Test successful Slack notification."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        writer = FeedbackWriter(mode="comment", slack_webhook="https://hooks.slack.com/test")
        feedbacks = [
            create_feedback(issue_key="TEST-1", score=50.0),
            create_feedback(issue_key="TEST-2", score=60.0),
        ]

        writer.send_slack_notification(feedbacks, limit=5)

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://hooks.slack.com/test"
        assert "blocks" in call_args[1]["json"]

    @patch("httpx.post")
    def test_send_slack_sorts_by_score(self, mock_post):
        """Test Slack notification sorts by lowest score first."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        writer = FeedbackWriter(mode="comment", slack_webhook="https://hooks.slack.com/test")
        feedbacks = [
            create_feedback(issue_key="HIGH", score=90.0),
            create_feedback(issue_key="LOW", score=30.0),
            create_feedback(issue_key="MID", score=60.0),
        ]

        writer.send_slack_notification(feedbacks, limit=2)

        call_args = mock_post.call_args
        blocks = call_args[1]["json"]["blocks"]
        # Find the section blocks with issue data
        issue_blocks = [b for b in blocks if b.get("type") == "section" and "issue_key" not in str(b)]
        # LOW should appear before MID
        block_text = str(blocks)
        assert block_text.index("LOW") < block_text.index("MID")

    @patch("httpx.post")
    def test_send_slack_failure(self, mock_post):
        """Test Slack notification with API failure."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        writer = FeedbackWriter(mode="comment", slack_webhook="https://hooks.slack.com/test")
        feedbacks = [create_feedback()]

        # Should not raise, just log warning
        writer.send_slack_notification(feedbacks)

    @patch("httpx.post")
    def test_send_slack_network_error(self, mock_post):
        """Test Slack notification with network error."""
        mock_post.side_effect = httpx.TimeoutException("Connection timeout")

        writer = FeedbackWriter(mode="comment", slack_webhook="https://hooks.slack.com/test")
        feedbacks = [create_feedback()]

        # Should not raise, just log warning
        writer.send_slack_notification(feedbacks)


class TestTelegramNotification:
    """Tests for Telegram notification functionality."""

    def test_no_token_configured(self):
        """Should not error when Telegram not configured."""
        writer = FeedbackWriter(mode="comment")
        feedbacks = [create_feedback(score=50)]
        writer.send_telegram_notification(feedbacks)  # Should not raise

    def test_no_chat_id_configured(self):
        """Should not send when chat_id missing."""
        writer = FeedbackWriter(mode="comment", telegram_bot_token="token")
        feedbacks = [create_feedback(score=50)]
        writer.send_telegram_notification(feedbacks)  # Should not raise

    def test_empty_feedbacks(self):
        """Should not send when no feedbacks."""
        writer = FeedbackWriter(
            mode="comment",
            telegram_bot_token="token",
            telegram_chat_id="123"
        )
        writer.send_telegram_notification([])  # Should not raise

    @patch("httpx.post")
    def test_successful_notification(self, mock_post):
        """Should send formatted message to Telegram API."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        writer = FeedbackWriter(
            mode="comment",
            telegram_bot_token="test_token",
            telegram_chat_id="test_chat"
        )
        feedbacks = [
            create_feedback(issue_key="TEST-1", score=45),
            create_feedback(issue_key="TEST-2", score=75),
        ]

        writer.send_telegram_notification(feedbacks)

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "api.telegram.org" in call_args[0][0]
        assert call_args[1]["json"]["chat_id"] == "test_chat"
        assert "TEST-1" in call_args[1]["json"]["text"]

    @patch("httpx.post")
    def test_sorts_by_score(self, mock_post):
        """Should sort feedbacks by score (lowest first)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        writer = FeedbackWriter(
            mode="comment",
            telegram_bot_token="token",
            telegram_chat_id="chat"
        )
        feedbacks = [
            create_feedback(issue_key="HIGH", score=90),
            create_feedback(issue_key="LOW", score=30),
            create_feedback(issue_key="MID", score=60),
        ]

        writer.send_telegram_notification(feedbacks, limit=2)

        text = mock_post.call_args[1]["json"]["text"]
        low_pos = text.find("LOW")
        mid_pos = text.find("MID")
        high_pos = text.find("HIGH")

        assert low_pos < mid_pos  # LOW should appear before MID
        assert high_pos == -1     # HIGH should not appear (limit=2)

    @patch("httpx.post")
    def test_api_failure(self, mock_post):
        """Should handle API failure gracefully."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        writer = FeedbackWriter(
            mode="comment",
            telegram_bot_token="token",
            telegram_chat_id="chat"
        )
        feedbacks = [create_feedback(score=50)]

        # Should not raise
        writer.send_telegram_notification(feedbacks)

    @patch("httpx.post")
    def test_network_error(self, mock_post):
        """Should handle network errors gracefully."""
        mock_post.side_effect = httpx.TimeoutException("Timeout")

        writer = FeedbackWriter(
            mode="comment",
            telegram_bot_token="token",
            telegram_chat_id="chat"
        )
        feedbacks = [create_feedback(score=50)]

        # Should not raise
        writer.send_telegram_notification(feedbacks)

    @patch("httpx.post")
    def test_message_format(self, mock_post):
        """Should format message with Markdown."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        writer = FeedbackWriter(
            mode="comment",
            telegram_bot_token="token",
            telegram_chat_id="chat"
        )
        feedbacks = [create_feedback(issue_key="TEST-1", score=50)]

        writer.send_telegram_notification(feedbacks)

        call_args = mock_post.call_args
        assert call_args[1]["json"]["parse_mode"] == "Markdown"
        text = call_args[1]["json"]["text"]
        assert "🔔" in text
        assert "*Jira Feedback Summary" in text


class TestGenerateSummaryReport:
    """Tests for generate_summary_report function."""

    def test_empty_feedbacks(self):
        """Test with empty feedback list."""
        result = generate_summary_report([])
        assert result == "No feedback generated."

    def test_basic_report(self):
        """Test basic report generation."""
        feedbacks = [
            create_feedback(issue_key="TEST-1", score=85.0),
            create_feedback(issue_key="TEST-2", score=65.0),
        ]

        result = generate_summary_report(feedbacks)

        assert "# Jira Feedback Summary Report" in result
        assert "Total issues analyzed: 2" in result
        assert "Average score:" in result

    def test_statistics_calculation(self):
        """Test statistics are calculated correctly."""
        feedbacks = [
            create_feedback(score=100.0),
            create_feedback(score=80.0),
            create_feedback(score=60.0),
        ]

        result = generate_summary_report(feedbacks)

        assert "Average score: 80.0/100" in result
        assert "Highest score: 100.0/100" in result
        assert "Lowest score: 60.0/100" in result

    def test_score_distribution(self):
        """Test score distribution table."""
        feedbacks = [
            create_feedback(issue_key="EXCELLENT", score=95.0),
            create_feedback(issue_key="GOOD", score=75.0),
            create_feedback(issue_key="POOR", score=45.0),
        ]

        result = generate_summary_report(feedbacks)

        assert "Score Distribution" in result
        assert "🌟 Excellent (90-100)" in result
        assert "👍 Good (70-80)" in result
        assert "🔧 Significant Issues (0-60)" in result

    def test_top_issues_needing_attention(self):
        """Test top issues section lists lowest scores first."""
        feedbacks = [
            create_feedback(issue_key="HIGH", score=95.0),
            create_feedback(issue_key="LOW", score=25.0),
            create_feedback(issue_key="MID", score=55.0),
        ]

        result = generate_summary_report(feedbacks)

        assert "Top 10 Issues Needing Attention" in result
        # In the "Top 10 Issues" section, LOW should appear before MID
        # Find position after the section header to avoid matching score distribution table
        top_section_start = result.find("Top 10 Issues Needing Attention")
        low_pos = result.find("LOW", top_section_start)
        mid_pos = result.find("MID", top_section_start)
        high_pos = result.find("HIGH", top_section_start)
        assert low_pos < mid_pos < high_pos

    def test_write_to_file(self, tmp_path):
        """Test writing report to file."""
        output_path = tmp_path / "summary" / "report.md"
        feedbacks = [create_feedback()]

        result = generate_summary_report(feedbacks, output_path=output_path)

        assert output_path.exists()
        content = output_path.read_text()
        assert content == result

    def test_creates_parent_directories(self, tmp_path):
        """Test creates parent directories if needed."""
        output_path = tmp_path / "deep" / "nested" / "report.md"
        feedbacks = [create_feedback()]

        generate_summary_report(feedbacks, output_path=output_path)

        assert output_path.exists()

    def test_more_than_five_issues_in_range(self):
        """Test handling more than 5 issues in a score range."""
        feedbacks = [
            create_feedback(issue_key=f"TEST-{i}", score=75.0)
            for i in range(10)
        ]

        result = generate_summary_report(feedbacks)

        assert "(+5 more)" in result

    def test_issues_below_70_count(self):
        """Test counting issues below 70."""
        feedbacks = [
            create_feedback(score=80.0),
            create_feedback(score=65.0),
            create_feedback(score=50.0),
            create_feedback(score=45.0),
        ]

        result = generate_summary_report(feedbacks)

        assert "Issues below 70: 3" in result
