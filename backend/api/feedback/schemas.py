"""Feedback Pydantic schemas."""

from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, Field


class FeedbackListRequest(BaseModel):
    """Schema for listing feedback."""

    issue_key: Optional[str] = None
    min_score: Optional[float] = Field(None, ge=0, le=100)
    max_score: Optional[float] = Field(None, ge=0, le=100)
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    limit: int = Field(default=50, le=100)
    offset: int = 0


class FeedbackSummaryResponse(BaseModel):
    """Schema for feedback list item."""

    id: int
    issue_key: str
    issue_summary: Optional[str]
    score: float
    emoji: str
    issue_type: Optional[str]
    assignee: Optional[str]
    was_posted_to_jira: bool
    created_at: datetime

    class Config:
        from_attributes = True


class FeedbackDetailResponse(BaseModel):
    """Schema for full feedback detail."""

    id: int
    issue_key: str
    issue_summary: Optional[str]
    score: float
    emoji: str
    overall_assessment: str
    strengths: list[str]
    improvements: list[str]
    suggestions: list[str]
    rubric_breakdown: dict[str, Any]
    improved_ac: Optional[str]
    resources: Optional[list[str]]
    issue_type: Optional[str]
    issue_status: Optional[str]
    assignee: Optional[str]
    labels: Optional[list[str]]
    was_posted_to_jira: bool
    was_sent_to_telegram: bool
    created_at: datetime

    class Config:
        from_attributes = True


class FeedbackStatsResponse(BaseModel):
    """Schema for feedback statistics."""

    total_analyzed: int
    average_score: float
    score_distribution: dict[str, int]  # {"90-100": 5, "80-90": 10, ...}
    issues_below_70: int
    top_improvement_areas: list[str]
    recent_count_7d: int
    recent_count_30d: int


class ScoreTrendItem(BaseModel):
    """Schema for score trend data point."""

    date: str
    average_score: float
    count: int


class ScoreTrendsResponse(BaseModel):
    """Schema for score trends over time."""

    trends: list[ScoreTrendItem]
    period_days: int


class TeamPerformanceItem(BaseModel):
    """Schema for team member performance."""

    assignee: str
    issues_count: int
    average_score: float
    trend: float  # Change from previous period


class TeamPerformanceResponse(BaseModel):
    """Schema for team performance data."""

    members: list[TeamPerformanceItem]
    period_days: int
