"""Main CLI application."""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.progress import track

from .cache import FeedbackCache
from .config import AppConfig
from .feedback_writer import FeedbackWriter, generate_summary_report
from .jira_client import JiraClient
from .pipeline import FeedbackPipeline

console = Console()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="DSPy Jira Feedback - Automated issue analysis and feedback"
    )

    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit (default behavior)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print feedback to console only, don't post to Jira"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of issues to process"
    )
    parser.add_argument(
        "--project",
        type=str,
        help="Filter to specific project (appends to JQL)"
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear the feedback cache before running"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show cache statistics and exit"
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to .env file (default: .env)"
    )

    args = parser.parse_args()

    try:
        # Load configuration
        if args.config:
            import os
            os.environ["ENV_FILE"] = args.config

        config = AppConfig.from_env()
        config.ensure_cache_dir()

        console.print(f"\n[bold cyan]DSPy Jira Feedback System[/bold cyan]\n")
        console.print(f"Mode: [yellow]{config.feedback_mode}[/yellow]")
        console.print(f"Model: [yellow]{config.model}[/yellow]")
        console.print(f"JQL: [dim]{config.jql}[/dim]\n")

        # Initialize cache
        cache = FeedbackCache(config.cache_db_path)

        # Handle --stats
        if args.stats:
            stats = cache.get_statistics()
            console.print(f"\n[bold]Cache Statistics:[/bold]")
            console.print(f"  Total issues commented: {stats['total_issues']}")
            console.print(f"  Total comments posted: {stats['total_comments']}")
            console.print(f"  Last activity: {stats['last_activity']}\n")
            cache.close()
            return 0

        # Handle --clear-cache
        if args.clear_cache:
            cache.clear()

        # Initialize Jira client
        jira_client = JiraClient(config.jira)

        # Build JQL
        jql = config.jql
        if args.project:
            jql += f" AND project = {args.project}"

        # Search for issues
        console.print(f"[cyan]Searching for issues...[/cyan]")
        issues = jira_client.search_issues(
            jql=jql,
            max_results=args.limit or 50
        )

        if not issues:
            console.print("[yellow]No issues found matching criteria[/yellow]")
            jira_client.close()
            cache.close()
            return 0

        # Filter issues that need feedback (check cache)
        issues_to_process = []
        for issue in issues:
            content_hash = issue.content_hash()
            if cache.should_comment(issue.key, content_hash):
                issues_to_process.append((issue, content_hash))

        if not issues_to_process:
            console.print("[green]All issues are up to date![/green]")
            jira_client.close()
            cache.close()
            return 0

        console.print(f"\n[bold]Processing {len(issues_to_process)} issues...[/bold]\n")

        # Initialize pipeline and writer
        pipeline = FeedbackPipeline(config)
        feedback_writer = FeedbackWriter(
            mode=config.feedback_mode,
            jira_client=jira_client if not args.dry_run else None,
            slack_webhook=config.slack_webhook_url
        )

        # Process issues
        all_feedbacks = []
        failed_count = 0
        critical_failures = []

        for issue, content_hash in track(issues_to_process, description="Analyzing issues"):
            try:
                # Generate feedback
                feedback = pipeline.generate_feedback(issue)
                all_feedbacks.append(feedback)

                # Deliver feedback
                success = feedback_writer.deliver(feedback, dry_run=args.dry_run)

                if success and not args.dry_run:
                    cache.mark_commented(issue.key, content_hash)

                # Track critical failures (score < 50)
                if feedback.score < 50:
                    critical_failures.append(issue.key)

            except Exception as e:
                console.log(f"[red]Failed to process {issue.key}: {e}[/red]")
                failed_count += 1

        # Generate summary
        console.print(f"\n[bold green]✓ Processing complete![/bold green]\n")
        console.print(f"  Processed: {len(all_feedbacks)}")
        console.print(f"  Failed: {failed_count}")

        if all_feedbacks:
            avg_score = sum(f.score for f in all_feedbacks) / len(all_feedbacks)
            console.print(f"  Average score: {avg_score:.1f}/100")
            console.print(f"  Critical issues (< 50): {len(critical_failures)}")

            # Generate summary report if in report mode
            if config.feedback_mode == "report":
                timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
                summary_path = Path("reports") / f"{timestamp}_summary.md"
                generate_summary_report(all_feedbacks, summary_path)

            # Send Slack notification if configured
            if config.slack_webhook_url and not args.dry_run:
                feedback_writer.send_slack_notification(all_feedbacks, limit=10)

        # Cleanup
        jira_client.close()
        cache.close()

        # Exit with non-zero if critical failures
        if critical_failures:
            console.print(f"\n[yellow]⚠️  Critical issues found: {', '.join(critical_failures)}[/yellow]")
            return 1

        return 0

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        return 130

    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        import traceback
        console.print(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
