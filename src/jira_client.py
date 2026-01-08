"""Jira client wrapper using MCP tool integration."""

import base64
import hashlib
import time
from typing import Any, Optional

import httpx
from rich.console import Console

from .config import JiraAuthConfig
from .exceptions import (
    JiraAPIError,
    JiraAuthenticationError,
    JiraNotFoundError,
    JiraPermissionError,
    JiraRateLimitError,
)

console = Console()

# Input validation limits
MAX_TITLE_LENGTH = 500
MAX_DESCRIPTION_LENGTH = 50000


class JiraIssue:
    """Simplified Jira issue representation."""

    def __init__(self, data: dict[str, Any]):
        self.raw = data
        self.key: str = data.get("key", "")
        self.fields = data.get("fields", {})

    @property
    def summary(self) -> str:
        title = self.fields.get("summary", "")
        if len(title) > MAX_TITLE_LENGTH:
            return title[:MAX_TITLE_LENGTH] + "..."
        return title

    @property
    def description(self) -> str:
        desc = self.fields.get("description", "")
        # Handle Atlassian Document Format (ADF)
        if isinstance(desc, dict):
            desc = self._extract_text_from_adf(desc)
        desc = desc or ""
        if len(desc) > MAX_DESCRIPTION_LENGTH:
            return desc[:MAX_DESCRIPTION_LENGTH] + "..."
        return desc

    @property
    def labels(self) -> list[str]:
        return self.fields.get("labels", [])

    @property
    def assignee(self) -> Optional[str]:
        assignee = self.fields.get("assignee")
        if assignee:
            return assignee.get("displayName") or assignee.get("emailAddress", "")
        return None

    @property
    def issue_type(self) -> str:
        issue_type = self.fields.get("issuetype", {})
        return issue_type.get("name", "")

    @property
    def estimate(self) -> Optional[float]:
        """Get story points or time estimate."""
        # Try story points first (common custom fields)
        for field in ["customfield_10016", "customfield_10004", "customfield_10002"]:
            if field in self.fields and self.fields[field]:
                try:
                    return float(self.fields[field])
                except (ValueError, TypeError):
                    continue  # Field exists but not numeric

        # Try timetracking
        timetracking = self.fields.get("timetracking", {})
        if timetracking and "originalEstimate" in timetracking:
            try:
                return float(timetracking["originalEstimate"])
            except (ValueError, TypeError):
                pass

        return None

    @property
    def status(self) -> str:
        status = self.fields.get("status", {})
        return status.get("name", "")

    def _extract_text_from_adf(self, adf: dict) -> str:
        """Extract plain text from Atlassian Document Format."""
        if not isinstance(adf, dict):
            return str(adf)

        text_parts = []

        def extract_content(node):
            if isinstance(node, dict):
                if node.get("type") == "text":
                    text_parts.append(node.get("text", ""))
                if "content" in node:
                    for child in node["content"]:
                        extract_content(child)
            elif isinstance(node, list):
                for item in node:
                    extract_content(item)

        extract_content(adf)
        return " ".join(text_parts)

    def content_hash(self) -> str:
        """Generate hash of key fields for change detection."""
        content = f"{self.summary}|{self.description}|{','.join(self.labels)}|{self.estimate}"
        return hashlib.sha256(content.encode()).hexdigest()


class JiraClient:
    """
    Jira API client with MCP tool fallback.

    In production with MCP server, this would call MCP tools.
    For now, implements direct API calls with same interface.
    """

    def __init__(self, auth_config: JiraAuthConfig):
        self.config = auth_config
        self.client = httpx.Client(timeout=30.0)
        self._setup_headers()

    def __enter__(self) -> "JiraClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Context manager exit - ensure client is closed."""
        self.close()
        return False

    def _setup_headers(self) -> None:
        """Configure common headers (not auth - auth is generated per-request)."""
        self.client.headers["Accept"] = "application/json"
        self.client.headers["Content-Type"] = "application/json"

    def _get_auth_header(self) -> dict[str, str]:
        """Generate auth header on-demand to avoid storing credentials in memory."""
        if self.config.method == "pat":
            credentials = f"{self.config.email}:{self.config.api_token}"
            encoded = base64.b64encode(credentials.encode()).decode()
            return {"Authorization": f"Basic {encoded}"}
        elif self.config.method == "oauth":
            return {"Authorization": f"Bearer {self.config.oauth_token}"}
        return {}

    def search_issues(
        self,
        jql: str,
        fields: Optional[list[str]] = None,
        max_results: int = 50,
        start_at: int = 0
    ) -> list[JiraIssue]:
        """
        Search issues using JQL.

        In MCP mode, this would call:
        mcp.call_tool("jira", "search_issues", {"jql": jql, "fields": fields})
        """
        if fields is None:
            fields = [
                "summary", "description", "labels", "assignee", "issuetype",
                "status", "timetracking", "customfield_10016", "customfield_10004",
                "customfield_10002", "comment"
            ]

        params = {
            "jql": jql,
            "fields": ",".join(fields),
            "maxResults": max_results,
            "startAt": start_at
        }

        try:
            console.log(f"[cyan]Searching Jira with JQL:[/cyan] {jql}")
            response = self._request_with_retry(
                "GET",
                f"{self.config.base_url}/rest/api/3/search",
                params=params
            )

            issues_data = response.get("issues", [])
            console.log(f"[green]Found {len(issues_data)} issues[/green]")
            return [JiraIssue(data) for data in issues_data]

        except (JiraAPIError, httpx.HTTPError) as e:
            console.log(f"[red]Failed to search issues: {e}[/red]")
            raise

    def get_issue(self, key: str) -> JiraIssue:
        """
        Get a single issue by key.

        In MCP mode: mcp.call_tool("jira", "get_issue", {"key": key})
        """
        try:
            console.log(f"[cyan]Fetching issue:[/cyan] {key}")
            response = self._request_with_retry(
                "GET",
                f"{self.config.base_url}/rest/api/3/issue/{key}"
            )
            return JiraIssue(response)

        except (JiraAPIError, httpx.HTTPError) as e:
            console.log(f"[red]Failed to get issue {key}: {e}[/red]")
            raise

    def add_comment(self, key: str, body: str) -> dict:
        """
        Add a comment to an issue.

        In MCP mode: mcp.call_tool("jira", "add_comment", {"key": key, "body": body})
        """
        # Convert markdown to Atlassian Document Format
        adf_body = self._markdown_to_adf(body)

        payload = {"body": adf_body}

        try:
            console.log(f"[cyan]Adding comment to:[/cyan] {key}")
            response = self._request_with_retry(
                "POST",
                f"{self.config.base_url}/rest/api/3/issue/{key}/comment",
                json=payload
            )
            console.log(f"[green]Comment added successfully[/green]")
            return response

        except (JiraAPIError, httpx.HTTPError) as e:
            console.log(f"[red]Failed to add comment to {key}: {e}[/red]")
            raise

    def _request_with_retry(
        self,
        method: str,
        url: str,
        max_retries: int = 3,
        **kwargs
    ) -> dict:
        """Make HTTP request with exponential backoff retry."""
        # Add auth header for this request only (on-demand)
        headers = kwargs.pop("headers", {})
        headers.update(self._get_auth_header())

        last_exception: Exception | None = None

        for attempt in range(max_retries):
            try:
                response = self.client.request(method, url, headers=headers, **kwargs)
                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status == 429:  # Rate limited
                    retry_after = int(e.response.headers.get("Retry-After", 2 ** attempt))
                    console.log(f"[yellow]Rate limited, waiting {retry_after}s...[/yellow]")
                    time.sleep(retry_after)
                    last_exception = JiraRateLimitError(
                        f"Rate limited on {method} {url}", retry_after=retry_after
                    )
                    continue
                # Convert HTTP status errors to specific Jira exceptions
                elif status == 401:
                    raise JiraAuthenticationError(f"Authentication failed for {url}") from e
                elif status == 403:
                    raise JiraPermissionError(f"Permission denied for {url}") from e
                elif status == 404:
                    raise JiraNotFoundError(f"Resource not found: {url}") from e
                else:
                    raise JiraAPIError(
                        f"Jira API error: {e.response.text[:200]}", status_code=status
                    ) from e

            except httpx.TimeoutException as e:
                wait_time = 2 ** attempt
                console.log(f"[yellow]Request timeout, retrying in {wait_time}s...[/yellow]")
                time.sleep(wait_time)
                last_exception = e

            except httpx.RequestError as e:
                if attempt == max_retries - 1:
                    raise
                wait_time = 2 ** attempt
                console.log(f"[yellow]Request failed, retrying in {wait_time}s...[/yellow]")
                time.sleep(wait_time)
                last_exception = e

        raise JiraAPIError(f"Max retries exceeded for {method} {url}") from last_exception

    def _markdown_to_adf(self, markdown: str) -> dict:
        """
        Convert markdown to Atlassian Document Format.
        This is a simplified version - in production, use a proper converter.
        """
        paragraphs = []

        for line in markdown.split("\n"):
            line = line.strip()
            if not line:
                continue

            # Headers
            if line.startswith("###"):
                paragraphs.append({
                    "type": "heading",
                    "attrs": {"level": 3},
                    "content": [{"type": "text", "text": line[3:].strip()}]
                })
            elif line.startswith("##"):
                paragraphs.append({
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [{"type": "text", "text": line[2:].strip()}]
                })
            elif line.startswith("#"):
                paragraphs.append({
                    "type": "heading",
                    "attrs": {"level": 1},
                    "content": [{"type": "text", "text": line[1:].strip()}]
                })
            # Bullet lists
            elif line.startswith("- ") or line.startswith("* "):
                paragraphs.append({
                    "type": "bulletList",
                    "content": [{
                        "type": "listItem",
                        "content": [{
                            "type": "paragraph",
                            "content": [{"type": "text", "text": line[2:].strip()}]
                        }]
                    }]
                })
            # Regular paragraph
            else:
                paragraphs.append({
                    "type": "paragraph",
                    "content": [{"type": "text", "text": line}]
                })

        return {
            "type": "doc",
            "version": 1,
            "content": paragraphs
        }

    def close(self):
        """Close HTTP client."""
        self.client.close()
