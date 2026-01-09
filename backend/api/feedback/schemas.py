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


# ============================================================
# Revision Tracking Schemas
# ============================================================


class FeedbackRevisionInfo(BaseModel):
    """Schema for revision information."""

    revision_number: int
    previous_feedback_id: Optional[int]
    previous_score: Optional[float]
    score_improvement: Optional[float]
    is_passing: bool


class RevisionSummary(BaseModel):
    """Schema for a revision in the history."""

    id: int
    revision_number: int
    score: float
    emoji: str
    is_passing: bool
    content_hash: str
    created_at: datetime

    class Config:
        from_attributes = True


class IssueRevisionHistoryResponse(BaseModel):
    """Schema for issue revision history."""

    issue_key: str
    issue_summary: Optional[str]
    revisions: list[RevisionSummary]
    total_revisions: int
    revisions_to_pass: Optional[int]  # None if not yet passing
    first_score: float
    latest_score: float
    score_improvement: float  # From first to latest


class RevisionStatsResponse(BaseModel):
    """Schema for aggregate revision statistics."""

    total_issues_with_revisions: int
    average_revisions_per_issue: float
    average_revisions_to_pass: Optional[float]
    issues_improved_after_revision: int
    average_score_improvement: float


# ============================================================
# Student Progress Dashboard Schemas
# ============================================================


class MilestoneItem(BaseModel):
    """Schema for student achievement milestone."""

    type: str  # "first_passing", "streak", "improvement", "perfect_score", "consistent_quality"
    title: str
    description: str
    achieved_at: datetime
    issue_key: Optional[str] = None


class StudentSummaryItem(BaseModel):
    """Schema for student list item."""

    assignee: str
    total_issues: int
    average_score: float
    passing_rate: float  # Percentage of issues with score >= 70
    trend: float  # Change from previous period
    latest_activity: Optional[datetime]


class StudentProgressResponse(BaseModel):
    """Schema for full student progress dashboard."""

    assignee: str
    total_issues: int
    average_score: float
    passing_rate: float
    score_trend: list[ScoreTrendItem]  # Personal timeline
    skill_breakdown: dict[str, float]  # rule_id -> avg score (0-100)
    class_comparison: dict[str, float]  # rule_id -> difference from class avg
    milestones: list[MilestoneItem]
    recent_feedbacks: list["FeedbackSummaryResponse"]


class SkillRadarData(BaseModel):
    """Schema for radar chart data."""

    skills: list[str]  # Skill names
    skill_ids: list[str]  # rule_ids for reference
    student_scores: list[float]  # 0-100 scale
    class_average_scores: list[float]  # 0-100 scale


class StudentsListResponse(BaseModel):
    """Schema for students list."""

    students: list[StudentSummaryItem]
    total_students: int
    class_average_score: float


# ============================================================
# Grade Export Schemas
# ============================================================


class GradeExportRequest(BaseModel):
    """Schema for grade export request."""

    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    grade_mapping: Optional[dict[str, list[float]]] = None
    # Default: {"A": [90, 100], "B": [80, 89.99], "C": [70, 79.99], "D": [60, 69.99], "F": [0, 59.99]}
    include_individual_issues: bool = False


class StudentGradeRecord(BaseModel):
    """Schema for individual student grade record."""

    student_name: str
    issue_count: int
    average_score: float
    trend: float
    letter_grade: str
    passing_rate: float


class GradeExportPreviewResponse(BaseModel):
    """Schema for grade export preview."""

    records: list[StudentGradeRecord]
    total_students: int
    class_average: float
    date_range: str


# ============================================================
# Skill Gap Analysis Schemas
# ============================================================


class WeakAreaItem(BaseModel):
    """Schema for weak area identification."""

    rule_id: str
    rule_name: str
    average_score: float  # 0-100 scale
    students_struggling: int  # Count with score < 70% on this rule
    improvement_trend: float  # Change over time


class StudentGapItem(BaseModel):
    """Schema for per-student skill gap."""

    assignee: str
    skill_gaps: list[str]  # rule_ids where student is below class avg
    biggest_gap_rule: str
    biggest_gap_amount: float  # How much below class avg


class SkillTrendPoint(BaseModel):
    """Schema for skill trend data point."""

    date: str
    average_score: float
    sample_size: int


class SkillGapAnalysisResponse(BaseModel):
    """Schema for class-wide skill gap analysis."""

    overall_stats: dict[str, float]  # rule_id -> class avg score (0-100)
    rule_names: dict[str, str]  # rule_id -> human readable name
    time_series: dict[str, list[SkillTrendPoint]]  # rule_id -> scores over time
    weak_areas: list[WeakAreaItem]  # Sorted by avg score, lowest first
    strong_areas: list[WeakAreaItem]  # Sorted by avg score, highest first
    student_gaps: list[StudentGapItem]  # Per-student gaps


class SkillDetailResponse(BaseModel):
    """Schema for detailed skill analysis."""

    rule_id: str
    rule_name: str
    class_average: float
    trend_data: list[SkillTrendPoint]
    score_distribution: dict[str, int]  # {"90-100": 5, "80-89": 10, ...}
    students_by_performance: dict[str, list[str]]  # {"excellent": ["John"], "struggling": ["Jane"]}
    improvement_suggestions: list[str]
