"""Feedback formatting and delivery."""

import fcntl
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
from rich.console import Console
from rich.markdown import Markdown

from .exceptions import JiraAPIError
from .jira_client import JiraClient
from .pipeline import Feedback

console = Console()


class FeedbackWriter:
    """Format and write feedback as comments or reports."""

    def __init__(self, mode: str, jira_client: Optional[JiraClient] = None, slack_webhook: Optional[str] = None):
        self.mode = mode
        self.jira_client = jira_client
        self.slack_webhook = slack_webhook

    def deliver(self, feedback: Feedback, dry_run: bool = False) -> bool:
        """
        Deliver feedback based on configured mode.

        Args:
            feedback: Feedback object to deliver
            dry_run: If True, only print to console

        Returns:
            True if successfully delivered
        """
        if dry_run:
            console.print(f"\n[bold yellow]DRY RUN - Would deliver feedback for {feedback.issue_key}[/bold yellow]")
            self._print_feedback(feedback)
            return True

        if self.mode == "comment":
            return self._post_comment(feedback)
        elif self.mode == "report":
            return self._append_to_report(feedback)
        else:
            console.log(f"[red]Unknown feedback mode: {self.mode}[/red]")
            return False

    def _print_feedback(self, feedback: Feedback):
        """Print feedback to console."""
        markdown_text = self._format_as_markdown(feedback)
        console.print(Markdown(markdown_text))

    def _post_comment(self, feedback: Feedback) -> bool:
        """Post feedback as Jira comment."""
        if not self.jira_client:
            console.log("[red]Jira client required for comment mode[/red]")
            return False

        try:
            markdown = self._format_as_markdown(feedback)
            self.jira_client.add_comment(feedback.issue_key, markdown)
            console.log(f"[green]✓ Comment posted to {feedback.issue_key}[/green]")
            return True

        except (JiraAPIError, httpx.HTTPError) as e:
            console.log(f"[red]Failed to post comment: {e}[/red]")
            return False

    def _append_to_report(self, feedback: Feedback) -> bool:
        """Append feedback to markdown report file with file locking for concurrency safety."""
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)

        # Use date-based filename
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
        report_path = reports_dir / f"{timestamp}_report.md"

        try:
            # Use exclusive file locking to prevent race conditions
            with open(report_path, "a+", encoding="utf-8") as f:
                # Acquire exclusive lock
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    # Move to beginning to read existing content
                    f.seek(0)
                    content = f.read()

                    # If file is empty, add header
                    if not content:
                        content = f"# Jira Feedback Report\n\nGenerated: {datetime.now().isoformat()}\n\n"
                        content += "---\n\n"

                    # Append this feedback
                    content += self._format_as_markdown(feedback)
                    content += "\n\n---\n\n"

                    # Truncate and write
                    f.seek(0)
                    f.truncate()
                    f.write(content)
                finally:
                    # Release lock
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

            console.log(f"[green]✓ Appended to report: {report_path}[/green]")
            return True

        except (OSError, IOError) as e:
            console.log(f"[red]Failed to write report: {e}[/red]")
            return False

    def _format_as_markdown(self, feedback: Feedback) -> str:
        """Format feedback as markdown."""
        lines = []

        # Header
        lines.append(f"## {feedback.emoji} Feedback for {feedback.issue_key}")
        lines.append(f"\n**Score:** {feedback.score}/100\n")

        # Overall assessment
        lines.append(f"### Overall Assessment\n")
        lines.append(f"{feedback.overall_assessment}\n")

        # Strengths
        if feedback.strengths:
            lines.append(f"### ✅ Strengths\n")
            for strength in feedback.strengths:
                lines.append(f"- {strength}")
            lines.append("")

        # Areas for improvement
        if feedback.improvements:
            lines.append(f"### 🔧 Areas for Improvement\n")
            for improvement in feedback.improvements:
                lines.append(f"- {improvement}")
            lines.append("")

        # Actionable suggestions
        if feedback.suggestions:
            lines.append(f"### 💡 Actionable Suggestions\n")
            for i, suggestion in enumerate(feedback.suggestions, 1):
                lines.append(f"{i}. {suggestion}")
            lines.append("")

        # Improved AC
        if feedback.improved_ac:
            lines.append(f"### 📋 Proposed Acceptance Criteria\n")
            lines.append(f"```\n{feedback.improved_ac}\n```\n")

        # Resources
        if feedback.resources:
            lines.append(f"### 📚 Helpful Resources\n")
            for resource in feedback.resources:
                lines.append(f"- {resource}")
            lines.append("")

        # Rubric breakdown (collapsible)
        if feedback.rubric_breakdown:
            lines.append(f"<details>\n<summary>Detailed Rubric Breakdown</summary>\n")
            for rule_id, details in feedback.rubric_breakdown.items():
                lines.append(f"\n**{rule_id}:** {details['score']}/100")
                lines.append(f"- {details['message']}")
                if details.get('suggestion'):
                    lines.append(f"- *Suggestion:* {details['suggestion']}")
            lines.append(f"\n</details>\n")

        # Footer
        lines.append(f"\n---")
        lines.append(f"*Generated by DSPy Jira Feedback • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

        return "\n".join(lines)

    def send_slack_notification(self, feedbacks: list[Feedback], limit: int = 10):
        """Send Slack notification with top issues needing attention."""
        if not self.slack_webhook:
            return

        # Sort by score (lowest first)
        sorted_feedbacks = sorted(feedbacks, key=lambda f: f.score)[:limit]

        if not sorted_feedbacks:
            return

        # Build Slack message
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🔔 Jira Feedback Summary - {datetime.now().strftime('%Y-%m-%d')}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Analyzed {len(feedbacks)} issues. Top {len(sorted_feedbacks)} needing attention:"
                }
            },
            {"type": "divider"}
        ]

        for fb in sorted_feedbacks:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{fb.issue_key}* - Score: {fb.score}/100 {fb.emoji}\n{fb.overall_assessment[:100]}..."
                }
            })

        try:
            response = httpx.post(
                self.slack_webhook,
                json={"blocks": blocks},
                timeout=10.0
            )
            if response.status_code == 200:
                console.log("[green]✓ Slack notification sent[/green]")
            else:
                console.log(f"[yellow]Slack notification failed: {response.status_code}[/yellow]")

        except httpx.HTTPError as e:
            console.log(f"[yellow]Failed to send Slack notification: {e}[/yellow]")


def generate_summary_report(feedbacks: list[Feedback], output_path: Optional[Path] = None) -> str:
    """Generate a summary report with statistics."""
    if not feedbacks:
        return "No feedback generated."

    lines = []
    lines.append("# Jira Feedback Summary Report\n")
    lines.append(f"Generated: {datetime.now().isoformat()}\n")
    lines.append(f"Total issues analyzed: {len(feedbacks)}\n")

    # Statistics
    scores = [f.score for f in feedbacks]
    avg_score = sum(scores) / len(scores)
    lines.append(f"## Statistics\n")
    lines.append(f"- Average score: {avg_score:.1f}/100")
    lines.append(f"- Highest score: {max(scores):.1f}/100")
    lines.append(f"- Lowest score: {min(scores):.1f}/100")
    lines.append(f"- Issues below 70: {sum(1 for s in scores if s < 70)}\n")

    # Score distribution
    lines.append(f"## Score Distribution\n")
    lines.append("| Range | Count | Issues |")
    lines.append("|-------|-------|--------|")

    ranges = [
        (90, 100, "🌟 Excellent"),
        (80, 90, "✅ Very Good"),
        (70, 80, "👍 Good"),
        (60, 70, "⚠️ Needs Work"),
        (0, 60, "🔧 Significant Issues")
    ]

    for min_s, max_s, label in ranges:
        in_range = [f for f in feedbacks if min_s <= f.score < max_s]
        keys = ", ".join([f.issue_key for f in in_range[:5]])
        if len(in_range) > 5:
            keys += f" (+{len(in_range) - 5} more)"
        lines.append(f"| {label} ({min_s}-{max_s}) | {len(in_range)} | {keys} |")

    lines.append("")

    # Top issues needing attention
    lines.append(f"## Top 10 Issues Needing Attention\n")
    sorted_low = sorted(feedbacks, key=lambda f: f.score)[:10]
    for i, fb in enumerate(sorted_low, 1):
        lines.append(f"{i}. **{fb.issue_key}** - {fb.score}/100 {fb.emoji}")
        lines.append(f"   - {fb.overall_assessment[:100]}...")
        lines.append("")

    report_text = "\n".join(lines)

    # Write to file if path provided
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_text)
        console.log(f"[green]Summary report written to {output_path}[/green]")

    return report_text
