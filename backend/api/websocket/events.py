"""WebSocket event types and schemas."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel


class EventType(str, Enum):
    """WebSocket event types."""

    # Connection events
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"

    # Job lifecycle events
    JOB_STARTED = "job_started"
    JOB_PROGRESS = "job_progress"
    JOB_COMPLETED = "job_completed"
    JOB_FAILED = "job_failed"
    JOB_CANCELLED = "job_cancelled"

    # Issue analysis events
    ISSUE_STARTED = "issue_started"
    ISSUE_RUBRIC_COMPLETE = "issue_rubric_complete"
    ISSUE_LLM_STARTED = "issue_llm_started"
    ISSUE_LLM_COMPLETE = "issue_llm_complete"
    ISSUE_COMPLETE = "issue_complete"
    ISSUE_FAILED = "issue_failed"

    # Delivery events
    JIRA_COMMENT_POSTED = "jira_comment_posted"
    TELEGRAM_SENT = "telegram_sent"

    # Activity events (for live feed)
    ACTIVITY = "activity"


class WebSocketEvent(BaseModel):
    """Base WebSocket event schema."""

    event: EventType
    timestamp: datetime
    data: dict[str, Any]

    @classmethod
    def create(cls, event_type: EventType, **data) -> "WebSocketEvent":
        """Create a new event with current timestamp."""
        return cls(
            event=event_type,
            timestamp=datetime.utcnow(),
            data=data,
        )


# Specific event data schemas for type safety
class ConnectedEventData(BaseModel):
    """Data for CONNECTED event."""

    message: str = "Connected to WebSocket"
    user_id: Optional[int] = None


class JobStartedEventData(BaseModel):
    """Data for JOB_STARTED event."""

    job_id: str
    jql: str
    total_issues: int
    dry_run: bool


class JobProgressEventData(BaseModel):
    """Data for JOB_PROGRESS event."""

    job_id: str
    current_issue: str
    processed: int
    total: int
    percent: float
    failed: int = 0


class IssueStartedEventData(BaseModel):
    """Data for ISSUE_STARTED event."""

    job_id: Optional[str] = None
    issue_key: str
    summary: str


class IssueRubricCompleteEventData(BaseModel):
    """Data for ISSUE_RUBRIC_COMPLETE event."""

    job_id: Optional[str] = None
    issue_key: str
    rubric_score: float
    rubric_breakdown: dict[str, dict]


class IssueLLMStartedEventData(BaseModel):
    """Data for ISSUE_LLM_STARTED event."""

    job_id: Optional[str] = None
    issue_key: str
    model: str


class IssueCompleteEventData(BaseModel):
    """Data for ISSUE_COMPLETE event."""

    job_id: Optional[str] = None
    issue_key: str
    score: float
    emoji: str
    assessment: str


class IssueFailedEventData(BaseModel):
    """Data for ISSUE_FAILED event."""

    job_id: Optional[str] = None
    issue_key: str
    error: str


class JobCompletedEventData(BaseModel):
    """Data for JOB_COMPLETED event."""

    job_id: str
    total_processed: int
    total_failed: int
    average_score: Optional[float]
    duration_seconds: float


class JobFailedEventData(BaseModel):
    """Data for JOB_FAILED event."""

    job_id: str
    error: str


class ActivityEventData(BaseModel):
    """Data for ACTIVITY event (live feed)."""

    type: str  # "analysis", "comment", "error", etc.
    issue_key: Optional[str] = None
    message: str
    level: str = "info"  # "info", "success", "warning", "error"
