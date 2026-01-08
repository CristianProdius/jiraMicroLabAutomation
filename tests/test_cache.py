"""Tests for feedback cache."""

import tempfile
from pathlib import Path

import pytest

from src.cache import FeedbackCache


@pytest.fixture
def temp_cache():
    """Create a temporary cache for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / "test_cache.sqlite"
        cache = FeedbackCache(cache_path)
        yield cache
        cache.close()


class TestFeedbackCache:
    """Test cache functionality."""

    def test_init_creates_database(self):
        """Test that cache initialization creates database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "test.sqlite"
            cache = FeedbackCache(cache_path)

            assert cache_path.exists()
            cache.close()

    def test_should_comment_new_issue(self, temp_cache):
        """Test that new issues should be commented on."""
        should = temp_cache.should_comment("TEST-123", "hash123")
        assert should is True

    def test_should_comment_same_hash(self, temp_cache):
        """Test that same hash prevents duplicate comment."""
        temp_cache.mark_commented("TEST-123", "hash123")
        should = temp_cache.should_comment("TEST-123", "hash123")
        assert should is False

    def test_should_comment_different_hash(self, temp_cache):
        """Test that changed content allows new comment."""
        temp_cache.mark_commented("TEST-123", "hash123")
        should = temp_cache.should_comment("TEST-123", "hash456")
        assert should is True

    def test_mark_commented_increments_count(self, temp_cache):
        """Test that marking increments comment count."""
        temp_cache.mark_commented("TEST-123", "hash123")
        temp_cache.mark_commented("TEST-123", "hash456")

        stats = temp_cache.get_statistics()
        assert stats["total_issues"] == 1
        # Note: total_comments reflects the count in the DB

    def test_get_statistics_empty(self, temp_cache):
        """Test statistics on empty cache."""
        stats = temp_cache.get_statistics()

        assert stats["total_issues"] == 0
        assert stats["total_comments"] == 0

    def test_get_statistics_with_data(self, temp_cache):
        """Test statistics with data."""
        temp_cache.mark_commented("TEST-123", "hash1")
        temp_cache.mark_commented("TEST-456", "hash2")

        stats = temp_cache.get_statistics()

        assert stats["total_issues"] == 2
        assert stats["total_comments"] == 2
        assert stats["last_activity"] != "Never"

    def test_clear_cache(self, temp_cache):
        """Test clearing cache."""
        temp_cache.mark_commented("TEST-123", "hash1")
        temp_cache.mark_commented("TEST-456", "hash2")

        temp_cache.clear()
        stats = temp_cache.get_statistics()

        assert stats["total_issues"] == 0
        assert stats["total_comments"] == 0
