"""Feedback history database models."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import relationship

from api.db.database import Base

if TYPE_CHECKING:
    from api.auth.models import User


class FeedbackHistory(Base):
    """Store feedback history for analytics and idempotency."""

    __tablename__ = "feedback_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    issue_key = Column(String(50), nullable=False, index=True)
    content_hash = Column(String(64), nullable=False)  # SHA256 hash

    # Feedback data
    score = Column(Float, nullable=False)
    emoji = Column(String(10), nullable=False)
    overall_assessment = Column(Text, nullable=False)
    strengths = Column(JSON, nullable=False)  # List of strings
    improvements = Column(JSON, nullable=False)  # List of strings
    suggestions = Column(JSON, nullable=False)  # List of strings
    rubric_breakdown = Column(JSON, nullable=False)
    improved_ac = Column(Text, nullable=True)
    resources = Column(JSON, nullable=True)  # List of helpful links

    # Issue metadata (denormalized for analytics)
    issue_summary = Column(String(500), nullable=True)
    issue_type = Column(String(50), nullable=True)
    issue_status = Column(String(50), nullable=True)
    assignee = Column(String(100), nullable=True)
    labels = Column(JSON, nullable=True)

    # Delivery tracking
    was_posted_to_jira = Column(Boolean, default=False)
    jira_comment_id = Column(String(100), nullable=True)
    was_sent_to_telegram = Column(Boolean, default=False)
    was_sent_to_slack = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = relationship("User", back_populates="feedback_history")


class AnalysisJob(Base):
    """Track long-running analysis jobs."""

    __tablename__ = "analysis_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(36), unique=True, nullable=False, index=True)  # UUID
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Job configuration
    jql = Column(String(1000), nullable=False)
    max_issues = Column(Integer, default=50)
    dry_run = Column(Boolean, default=False)
    post_to_jira = Column(Boolean, default=False)
    send_telegram = Column(Boolean, default=False)
    rubric_config_id = Column(Integer, ForeignKey("user_rubric_configs.id", ondelete="SET NULL"), nullable=True)

    # Status tracking
    status = Column(String(20), default="pending")  # pending, running, completed, failed, cancelled
    total_issues = Column(Integer, default=0)
    processed_issues = Column(Integer, default=0)
    failed_issues = Column(Integer, default=0)
    current_issue_key = Column(String(50), nullable=True)

    # Results summary
    average_score = Column(Float, nullable=True)
    lowest_score = Column(Float, nullable=True)
    highest_score = Column(Float, nullable=True)

    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="analysis_jobs")
    rubric_config = relationship("UserRubricConfig")
