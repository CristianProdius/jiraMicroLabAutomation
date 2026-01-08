"""Issue-related Pydantic schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class IssueSearchRequest(BaseModel):
    """Schema for searching issues."""

    jql: str = Field(..., min_length=1, description="JQL query string")
    max_results: int = Field(default=50, le=100, ge=1)
    fields: Optional[list[str]] = None


class IssueResponse(BaseModel):
    """Schema for a single Jira issue."""

    key: str
    summary: str
    description: Optional[str] = None
    labels: list[str] = []
    assignee: Optional[str] = None
    issue_type: str
    estimate: Optional[float] = None
    status: str
    content_hash: str

    class Config:
        from_attributes = True


class IssueSearchResponse(BaseModel):
    """Schema for issue search results."""

    issues: list[IssueResponse]
    total: int


class AnalyzeSingleRequest(BaseModel):
    """Schema for analyzing a single issue."""

    rubric_config_id: Optional[int] = None
    post_to_jira: bool = False


class BatchAnalyzeRequest(BaseModel):
    """Schema for batch issue analysis."""

    jql: str = Field(..., min_length=1)
    max_issues: int = Field(default=50, le=100, ge=1)
    rubric_config_id: Optional[int] = None
    dry_run: bool = True
    post_to_jira: bool = False
    send_telegram: bool = False


class JobStatusResponse(BaseModel):
    """Schema for analysis job status."""

    job_id: str
    status: str  # pending, running, completed, failed, cancelled
    total_issues: int
    processed_issues: int
    failed_issues: int
    progress_percent: float
    current_issue_key: Optional[str] = None
    average_score: Optional[float] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class RubricResultResponse(BaseModel):
    """Schema for a single rubric evaluation result."""

    rule_id: str
    rule_name: str
    score: float  # 0-100 (converted from 0-1)
    weight: float
    message: str
    suggestion: Optional[str] = None


class FeedbackResponse(BaseModel):
    """Schema for feedback on an issue."""

    id: int
    issue_key: str
    score: float
    emoji: str
    overall_assessment: str
    strengths: list[str]
    improvements: list[str]
    suggestions: list[str]
    rubric_breakdown: list[RubricResultResponse]
    improved_ac: Optional[str] = None
    resources: Optional[list[str]] = None
    was_posted_to_jira: bool
    created_at: datetime

    class Config:
        from_attributes = True
