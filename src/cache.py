"""SQLite-based cache for idempotency tracking."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console

console = Console()


class FeedbackCache:
    """SQLite cache to track which issues have been commented on."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS feedback_cache (
                issue_key TEXT PRIMARY KEY,
                last_hash TEXT NOT NULL,
                last_commented_at TEXT NOT NULL,
                comment_count INTEGER DEFAULT 1
            )
        """)
        self.conn.commit()
        console.log(f"[dim]Cache initialized at {self.db_path}[/dim]")

    def should_comment(self, issue_key: str, content_hash: str) -> bool:
        """
        Check if we should comment on this issue.

        Returns True if:
        - Issue has never been commented on, OR
        - Content hash has changed since last comment
        """
        if not self.conn:
            return True

        cursor = self.conn.execute(
            "SELECT last_hash FROM feedback_cache WHERE issue_key = ?",
            (issue_key,)
        )
        row = cursor.fetchone()

        if row is None:
            # Never commented on this issue
            console.log(f"[dim]{issue_key}: New issue, will comment[/dim]")
            return True

        last_hash = row[0]
        if last_hash != content_hash:
            # Content has changed
            console.log(f"[dim]{issue_key}: Content changed, will comment[/dim]")
            return True

        # Already commented with same content
        console.log(f"[dim]{issue_key}: Already commented with same content, skipping[/dim]")
        return False

    def mark_commented(self, issue_key: str, content_hash: str):
        """Record that we've commented on this issue."""
        if not self.conn:
            return

        now = datetime.utcnow().isoformat()

        # Check if exists
        cursor = self.conn.execute(
            "SELECT comment_count FROM feedback_cache WHERE issue_key = ?",
            (issue_key,)
        )
        row = cursor.fetchone()

        if row is None:
            # Insert new record
            self.conn.execute(
                """
                INSERT INTO feedback_cache (issue_key, last_hash, last_commented_at, comment_count)
                VALUES (?, ?, ?, 1)
                """,
                (issue_key, content_hash, now)
            )
        else:
            # Update existing record
            new_count = row[0] + 1
            self.conn.execute(
                """
                UPDATE feedback_cache
                SET last_hash = ?, last_commented_at = ?, comment_count = ?
                WHERE issue_key = ?
                """,
                (content_hash, now, new_count, issue_key)
            )

        self.conn.commit()
        console.log(f"[dim]{issue_key}: Marked as commented[/dim]")

    def get_statistics(self) -> dict:
        """Get cache statistics."""
        if not self.conn:
            return {}

        cursor = self.conn.execute("""
            SELECT
                COUNT(*) as total_issues,
                SUM(comment_count) as total_comments,
                MAX(last_commented_at) as last_activity
            FROM feedback_cache
        """)
        row = cursor.fetchone()

        return {
            "total_issues": row[0] or 0,
            "total_comments": row[1] or 0,
            "last_activity": row[2] or "Never"
        }

    def clear(self):
        """Clear all cache entries."""
        if self.conn:
            self.conn.execute("DELETE FROM feedback_cache")
            self.conn.commit()
            console.log("[yellow]Cache cleared[/yellow]")

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
