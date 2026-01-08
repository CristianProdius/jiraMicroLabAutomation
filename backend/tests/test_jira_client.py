"""Tests for jira_client module."""

import base64
from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.config import JiraAuthConfig
from src.jira_client import (
    JiraClient,
    JiraIssue,
    MAX_DESCRIPTION_LENGTH,
    MAX_TITLE_LENGTH,
)


class TestJiraIssue:
    """Tests for JiraIssue class."""

    def test_basic_properties(self):
        """Test basic issue properties."""
        data = {
            "key": "TEST-123",
            "fields": {
                "summary": "Test summary",
                "description": "Test description",
                "labels": ["bug", "urgent"],
                "status": {"name": "In Progress"},
                "issuetype": {"name": "Story"},
            },
        }
        issue = JiraIssue(data)

        assert issue.key == "TEST-123"
        assert issue.summary == "Test summary"
        assert issue.description == "Test description"
        assert issue.labels == ["bug", "urgent"]
        assert issue.status == "In Progress"
        assert issue.issue_type == "Story"

    def test_assignee_display_name(self):
        """Test assignee with display name."""
        data = {
            "key": "TEST-1",
            "fields": {
                "assignee": {"displayName": "John Doe", "emailAddress": "john@example.com"}
            },
        }
        issue = JiraIssue(data)
        assert issue.assignee == "John Doe"

    def test_assignee_fallback_to_email(self):
        """Test assignee falling back to email when no display name."""
        data = {
            "key": "TEST-1",
            "fields": {
                "assignee": {"emailAddress": "john@example.com"}
            },
        }
        issue = JiraIssue(data)
        assert issue.assignee == "john@example.com"

    def test_assignee_none(self):
        """Test unassigned issue."""
        data = {"key": "TEST-1", "fields": {"assignee": None}}
        issue = JiraIssue(data)
        assert issue.assignee is None

    def test_estimate_from_story_points(self):
        """Test estimate from story points custom field."""
        data = {
            "key": "TEST-1",
            "fields": {"customfield_10016": 8.0},
        }
        issue = JiraIssue(data)
        assert issue.estimate == 8.0

    def test_estimate_from_alternative_field(self):
        """Test estimate from alternative custom field."""
        data = {
            "key": "TEST-1",
            "fields": {"customfield_10004": 5.0},
        }
        issue = JiraIssue(data)
        assert issue.estimate == 5.0

    def test_estimate_from_string(self):
        """Test estimate conversion from string."""
        data = {
            "key": "TEST-1",
            "fields": {"customfield_10016": "3"},
        }
        issue = JiraIssue(data)
        assert issue.estimate == 3.0

    def test_estimate_invalid_value(self):
        """Test estimate with invalid value falls through to next field."""
        data = {
            "key": "TEST-1",
            "fields": {
                "customfield_10016": "not-a-number",
                "customfield_10004": 5.0,
            },
        }
        issue = JiraIssue(data)
        assert issue.estimate == 5.0

    def test_estimate_none(self):
        """Test issue without estimate."""
        data = {"key": "TEST-1", "fields": {}}
        issue = JiraIssue(data)
        assert issue.estimate is None

    def test_summary_truncation(self):
        """Test summary truncation for very long titles."""
        long_title = "A" * (MAX_TITLE_LENGTH + 100)
        data = {"key": "TEST-1", "fields": {"summary": long_title}}
        issue = JiraIssue(data)
        assert len(issue.summary) == MAX_TITLE_LENGTH + 3  # +3 for "..."
        assert issue.summary.endswith("...")

    def test_description_truncation(self):
        """Test description truncation for very long descriptions."""
        long_desc = "B" * (MAX_DESCRIPTION_LENGTH + 100)
        data = {"key": "TEST-1", "fields": {"description": long_desc}}
        issue = JiraIssue(data)
        assert len(issue.description) == MAX_DESCRIPTION_LENGTH + 3
        assert issue.description.endswith("...")

    def test_description_adf_extraction(self):
        """Test extraction of text from Atlassian Document Format."""
        adf_doc = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "First paragraph."},
                    ],
                },
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "Second paragraph."},
                    ],
                },
            ],
        }
        data = {"key": "TEST-1", "fields": {"description": adf_doc}}
        issue = JiraIssue(data)
        assert "First paragraph." in issue.description
        assert "Second paragraph." in issue.description

    def test_description_none(self):
        """Test issue with no description."""
        data = {"key": "TEST-1", "fields": {"description": None}}
        issue = JiraIssue(data)
        assert issue.description == ""

    def test_content_hash(self):
        """Test content hash generation."""
        data = {
            "key": "TEST-1",
            "fields": {
                "summary": "Test",
                "description": "Description",
                "labels": ["bug"],
                "customfield_10016": 5.0,
            },
        }
        issue = JiraIssue(data)
        hash1 = issue.content_hash()

        # Same data should produce same hash
        issue2 = JiraIssue(data.copy())
        assert issue2.content_hash() == hash1

    def test_content_hash_changes_with_content(self):
        """Test content hash changes when content changes."""
        data1 = {
            "key": "TEST-1",
            "fields": {"summary": "Test1", "description": "Desc"},
        }
        data2 = {
            "key": "TEST-1",
            "fields": {"summary": "Test2", "description": "Desc"},
        }
        issue1 = JiraIssue(data1)
        issue2 = JiraIssue(data2)
        assert issue1.content_hash() != issue2.content_hash()


class TestJiraClient:
    """Tests for JiraClient class."""

    @pytest.fixture
    def auth_config(self):
        """Create test auth config."""
        return JiraAuthConfig(
            base_url="https://test.atlassian.net",
            email="test@example.com",
            api_token="test-token",
            method="pat",
        )

    def test_init(self, auth_config):
        """Test client initialization."""
        client = JiraClient(auth_config)
        assert client.config == auth_config
        client.close()

    def test_context_manager(self, auth_config):
        """Test context manager protocol."""
        with JiraClient(auth_config) as client:
            assert client is not None
        # Client should be closed after exiting context

    def test_get_auth_header_pat(self, auth_config):
        """Test PAT authentication header generation."""
        client = JiraClient(auth_config)
        header = client._get_auth_header()

        expected_creds = "test@example.com:test-token"
        expected_encoded = base64.b64encode(expected_creds.encode()).decode()
        assert header == {"Authorization": f"Basic {expected_encoded}"}
        client.close()

    def test_get_auth_header_oauth(self):
        """Test OAuth authentication header generation."""
        config = JiraAuthConfig(
            base_url="https://test.atlassian.net",
            method="oauth",
            oauth_token="oauth-token-123",
        )
        client = JiraClient(config)
        header = client._get_auth_header()

        assert header == {"Authorization": "Bearer oauth-token-123"}
        client.close()


class TestJiraClientAPIMethods:
    """Tests for JiraClient API methods with mocked HTTP."""

    @pytest.fixture
    def mock_client(self):
        """Create client with mocked HTTP."""
        config = JiraAuthConfig(
            base_url="https://test.atlassian.net",
            email="test@example.com",
            api_token="test-token",
            method="pat",
        )
        client = JiraClient(config)
        yield client
        client.close()

    @patch.object(JiraClient, "_request_with_retry")
    def test_search_issues(self, mock_request, mock_client):
        """Test search_issues method."""
        mock_request.return_value = {
            "issues": [
                {"key": "TEST-1", "fields": {"summary": "Issue 1"}},
                {"key": "TEST-2", "fields": {"summary": "Issue 2"}},
            ]
        }

        issues = mock_client.search_issues("project = TEST")

        assert len(issues) == 2
        assert issues[0].key == "TEST-1"
        assert issues[1].key == "TEST-2"
        mock_request.assert_called_once()

    @patch.object(JiraClient, "_request_with_retry")
    def test_search_issues_with_custom_fields(self, mock_request, mock_client):
        """Test search_issues with custom fields."""
        mock_request.return_value = {"issues": []}

        mock_client.search_issues("project = TEST", fields=["summary", "status"])

        call_args = mock_request.call_args
        assert "summary,status" in str(call_args)

    @patch.object(JiraClient, "_request_with_retry")
    def test_get_issue(self, mock_request, mock_client):
        """Test get_issue method."""
        mock_request.return_value = {
            "key": "TEST-123",
            "fields": {"summary": "Test Issue"},
        }

        issue = mock_client.get_issue("TEST-123")

        assert issue.key == "TEST-123"
        assert issue.summary == "Test Issue"

    @patch.object(JiraClient, "_request_with_retry")
    def test_add_comment(self, mock_request, mock_client):
        """Test add_comment method."""
        mock_request.return_value = {"id": "12345"}

        result = mock_client.add_comment("TEST-123", "This is a comment")

        assert result == {"id": "12345"}
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[0][0] == "POST"
        assert "comment" in call_args[0][1]


class TestMarkdownToAdf:
    """Tests for markdown to ADF conversion."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        config = JiraAuthConfig(
            base_url="https://test.atlassian.net",
            email="test@example.com",
            api_token="test-token",
        )
        client = JiraClient(config)
        yield client
        client.close()

    def test_plain_paragraph(self, client):
        """Test plain paragraph conversion."""
        result = client._markdown_to_adf("Hello world")

        assert result["type"] == "doc"
        assert result["version"] == 1
        assert len(result["content"]) == 1
        assert result["content"][0]["type"] == "paragraph"
        assert result["content"][0]["content"][0]["text"] == "Hello world"

    def test_h1_heading(self, client):
        """Test H1 heading conversion."""
        result = client._markdown_to_adf("# Main Title")

        assert result["content"][0]["type"] == "heading"
        assert result["content"][0]["attrs"]["level"] == 1
        assert result["content"][0]["content"][0]["text"] == "Main Title"

    def test_h2_heading(self, client):
        """Test H2 heading conversion."""
        result = client._markdown_to_adf("## Section")

        assert result["content"][0]["attrs"]["level"] == 2

    def test_h3_heading(self, client):
        """Test H3 heading conversion."""
        result = client._markdown_to_adf("### Subsection")

        assert result["content"][0]["attrs"]["level"] == 3

    def test_bullet_list_dash(self, client):
        """Test bullet list with dash."""
        result = client._markdown_to_adf("- Item one")

        assert result["content"][0]["type"] == "bulletList"
        list_item = result["content"][0]["content"][0]
        assert list_item["type"] == "listItem"

    def test_bullet_list_asterisk(self, client):
        """Test bullet list with asterisk."""
        result = client._markdown_to_adf("* Item one")

        assert result["content"][0]["type"] == "bulletList"

    def test_multiline_content(self, client):
        """Test multiline content conversion."""
        markdown = """# Title
## Section
- Item 1
- Item 2
Some paragraph text"""

        result = client._markdown_to_adf(markdown)

        types = [node["type"] for node in result["content"]]
        assert "heading" in types
        assert "bulletList" in types
        assert "paragraph" in types

    def test_empty_lines_skipped(self, client):
        """Test that empty lines are skipped."""
        result = client._markdown_to_adf("Line 1\n\n\nLine 2")

        assert len(result["content"]) == 2


class TestJiraClientRetry:
    """Tests for retry logic."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        config = JiraAuthConfig(
            base_url="https://test.atlassian.net",
            email="test@example.com",
            api_token="test-token",
        )
        client = JiraClient(config)
        yield client
        client.close()

    @patch("time.sleep")
    def test_retry_on_rate_limit(self, mock_sleep, client):
        """Test retry on 429 rate limit."""
        mock_response_429 = MagicMock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {"Retry-After": "1"}

        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"success": True}
        mock_response_200.raise_for_status = MagicMock()

        with patch.object(client.client, "request") as mock_request:
            mock_request.side_effect = [
                httpx.HTTPStatusError("Rate limited", request=MagicMock(), response=mock_response_429),
                mock_response_200,
            ]

            result = client._request_with_retry("GET", "https://test.atlassian.net/api")

        assert result == {"success": True}
        assert mock_sleep.called

    @patch("time.sleep")
    def test_retry_on_timeout(self, mock_sleep, client):
        """Test retry on timeout."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_response.raise_for_status = MagicMock()

        with patch.object(client.client, "request") as mock_request:
            mock_request.side_effect = [
                httpx.TimeoutException("Timeout"),
                mock_response,
            ]

            result = client._request_with_retry("GET", "https://test.atlassian.net/api")

        assert result == {"success": True}
        assert mock_sleep.called

    @patch("time.sleep")
    def test_max_retries_exceeded(self, mock_sleep, client):
        """Test exception raised after max retries."""
        with patch.object(client.client, "request") as mock_request:
            mock_request.side_effect = httpx.TimeoutException("Timeout")

            with pytest.raises(Exception, match="Max retries exceeded"):
                client._request_with_retry("GET", "https://test.atlassian.net/api", max_retries=3)

        assert mock_request.call_count == 3
