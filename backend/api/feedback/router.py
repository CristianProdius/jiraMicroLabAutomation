"""Feedback API routes."""

from datetime import datetime, timedelta
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from api.dependencies import get_db, get_current_user
from api.auth.models import User
from api.feedback.models import FeedbackHistory
from api.feedback.schemas import (
    FeedbackListRequest,
    FeedbackSummaryResponse,
    FeedbackDetailResponse,
    FeedbackStatsResponse,
    ScoreTrendsResponse,
    ScoreTrendItem,
    TeamPerformanceResponse,
    TeamPerformanceItem,
)

router = APIRouter(prefix="/feedback", tags=["Feedback"])


@router.get("", response_model=list[FeedbackSummaryResponse])
async def list_feedback(
    issue_key: str = None,
    min_score: float = None,
    max_score: float = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List feedback history with optional filters."""
    query = db.query(FeedbackHistory).filter(FeedbackHistory.user_id == current_user.id)

    if issue_key:
        query = query.filter(FeedbackHistory.issue_key.ilike(f"%{issue_key}%"))
    if min_score is not None:
        query = query.filter(FeedbackHistory.score >= min_score)
    if max_score is not None:
        query = query.filter(FeedbackHistory.score <= max_score)

    feedbacks = (
        query.order_by(FeedbackHistory.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        FeedbackSummaryResponse(
            id=f.id,
            issue_key=f.issue_key,
            issue_summary=f.issue_summary,
            score=f.score,
            emoji=f.emoji,
            issue_type=f.issue_type,
            assignee=f.assignee,
            was_posted_to_jira=f.was_posted_to_jira,
            created_at=f.created_at,
        )
        for f in feedbacks
    ]


@router.get("/stats", response_model=FeedbackStatsResponse)
async def get_feedback_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get feedback statistics."""
    base_query = db.query(FeedbackHistory).filter(FeedbackHistory.user_id == current_user.id)

    # Total analyzed
    total_analyzed = base_query.count()

    if total_analyzed == 0:
        return FeedbackStatsResponse(
            total_analyzed=0,
            average_score=0,
            score_distribution={},
            issues_below_70=0,
            top_improvement_areas=[],
            recent_count_7d=0,
            recent_count_30d=0,
        )

    # Average score
    avg_result = base_query.with_entities(func.avg(FeedbackHistory.score)).scalar()
    average_score = round(avg_result or 0, 1)

    # Score distribution
    all_feedbacks = base_query.all()
    distribution = defaultdict(int)
    for f in all_feedbacks:
        if f.score >= 90:
            distribution["90-100"] += 1
        elif f.score >= 80:
            distribution["80-89"] += 1
        elif f.score >= 70:
            distribution["70-79"] += 1
        elif f.score >= 60:
            distribution["60-69"] += 1
        elif f.score >= 50:
            distribution["50-59"] += 1
        else:
            distribution["0-49"] += 1

    # Issues below 70
    issues_below_70 = base_query.filter(FeedbackHistory.score < 70).count()

    # Top improvement areas (from improvements field)
    improvement_counts = defaultdict(int)
    for f in all_feedbacks:
        if f.improvements:
            for improvement in f.improvements[:3]:  # Top 3 per issue
                # Extract key phrase
                key = improvement.split(":")[0] if ":" in improvement else improvement[:50]
                improvement_counts[key] += 1

    top_improvements = sorted(improvement_counts.keys(), key=lambda x: -improvement_counts[x])[:5]

    # Recent counts
    now = datetime.utcnow()
    recent_7d = base_query.filter(FeedbackHistory.created_at >= now - timedelta(days=7)).count()
    recent_30d = base_query.filter(FeedbackHistory.created_at >= now - timedelta(days=30)).count()

    return FeedbackStatsResponse(
        total_analyzed=total_analyzed,
        average_score=average_score,
        score_distribution=dict(distribution),
        issues_below_70=issues_below_70,
        top_improvement_areas=top_improvements,
        recent_count_7d=recent_7d,
        recent_count_30d=recent_30d,
    )


@router.get("/trends", response_model=ScoreTrendsResponse)
async def get_score_trends(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get score trends over time."""
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)

    feedbacks = (
        db.query(FeedbackHistory)
        .filter(
            FeedbackHistory.user_id == current_user.id,
            FeedbackHistory.created_at >= start_date,
        )
        .all()
    )

    # Group by date
    daily_data = defaultdict(list)
    for f in feedbacks:
        date_str = f.created_at.strftime("%Y-%m-%d")
        daily_data[date_str].append(f.score)

    # Build trend data
    trends = []
    current = start_date
    while current <= now:
        date_str = current.strftime("%Y-%m-%d")
        scores = daily_data.get(date_str, [])
        trends.append(
            ScoreTrendItem(
                date=date_str,
                average_score=round(sum(scores) / len(scores), 1) if scores else 0,
                count=len(scores),
            )
        )
        current += timedelta(days=1)

    return ScoreTrendsResponse(trends=trends, period_days=days)


@router.get("/team", response_model=TeamPerformanceResponse)
async def get_team_performance(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get team member performance metrics."""
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)
    prev_start = start_date - timedelta(days=days)

    # Current period
    current_feedbacks = (
        db.query(FeedbackHistory)
        .filter(
            FeedbackHistory.user_id == current_user.id,
            FeedbackHistory.created_at >= start_date,
            FeedbackHistory.assignee.isnot(None),
        )
        .all()
    )

    # Previous period for trend
    prev_feedbacks = (
        db.query(FeedbackHistory)
        .filter(
            FeedbackHistory.user_id == current_user.id,
            FeedbackHistory.created_at >= prev_start,
            FeedbackHistory.created_at < start_date,
            FeedbackHistory.assignee.isnot(None),
        )
        .all()
    )

    # Aggregate by assignee
    current_by_assignee = defaultdict(list)
    for f in current_feedbacks:
        current_by_assignee[f.assignee].append(f.score)

    prev_by_assignee = defaultdict(list)
    for f in prev_feedbacks:
        prev_by_assignee[f.assignee].append(f.score)

    # Build response
    members = []
    for assignee, scores in current_by_assignee.items():
        avg_current = sum(scores) / len(scores)
        prev_scores = prev_by_assignee.get(assignee, [])
        avg_prev = sum(prev_scores) / len(prev_scores) if prev_scores else avg_current
        trend = round(avg_current - avg_prev, 1)

        members.append(
            TeamPerformanceItem(
                assignee=assignee,
                issues_count=len(scores),
                average_score=round(avg_current, 1),
                trend=trend,
            )
        )

    # Sort by average score descending
    members.sort(key=lambda x: -x.average_score)

    return TeamPerformanceResponse(members=members, period_days=days)


@router.get("/{feedback_id}", response_model=FeedbackDetailResponse)
async def get_feedback(
    feedback_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get detailed feedback by ID."""
    feedback = (
        db.query(FeedbackHistory)
        .filter(
            FeedbackHistory.id == feedback_id,
            FeedbackHistory.user_id == current_user.id,
        )
        .first()
    )

    if not feedback:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found")

    return FeedbackDetailResponse(
        id=feedback.id,
        issue_key=feedback.issue_key,
        issue_summary=feedback.issue_summary,
        score=feedback.score,
        emoji=feedback.emoji,
        overall_assessment=feedback.overall_assessment,
        strengths=feedback.strengths,
        improvements=feedback.improvements,
        suggestions=feedback.suggestions,
        rubric_breakdown=feedback.rubric_breakdown,
        improved_ac=feedback.improved_ac,
        resources=feedback.resources,
        issue_type=feedback.issue_type,
        issue_status=feedback.issue_status,
        assignee=feedback.assignee,
        labels=feedback.labels,
        was_posted_to_jira=feedback.was_posted_to_jira,
        was_sent_to_telegram=feedback.was_sent_to_telegram,
        created_at=feedback.created_at,
    )


@router.get("/issue/{issue_key}", response_model=FeedbackDetailResponse)
async def get_feedback_by_issue(
    issue_key: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get latest feedback for an issue by key."""
    feedback = (
        db.query(FeedbackHistory)
        .filter(
            FeedbackHistory.issue_key == issue_key.upper(),
            FeedbackHistory.user_id == current_user.id,
        )
        .order_by(FeedbackHistory.created_at.desc())
        .first()
    )

    if not feedback:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No feedback found for this issue")

    return FeedbackDetailResponse(
        id=feedback.id,
        issue_key=feedback.issue_key,
        issue_summary=feedback.issue_summary,
        score=feedback.score,
        emoji=feedback.emoji,
        overall_assessment=feedback.overall_assessment,
        strengths=feedback.strengths,
        improvements=feedback.improvements,
        suggestions=feedback.suggestions,
        rubric_breakdown=feedback.rubric_breakdown,
        improved_ac=feedback.improved_ac,
        resources=feedback.resources,
        issue_type=feedback.issue_type,
        issue_status=feedback.issue_status,
        assignee=feedback.assignee,
        labels=feedback.labels,
        was_posted_to_jira=feedback.was_posted_to_jira,
        was_sent_to_telegram=feedback.was_sent_to_telegram,
        created_at=feedback.created_at,
    )


@router.post("/{feedback_id}/post-jira", status_code=status.HTTP_204_NO_CONTENT)
async def post_feedback_to_jira(
    feedback_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Post existing feedback as a comment to Jira."""
    feedback = (
        db.query(FeedbackHistory)
        .filter(
            FeedbackHistory.id == feedback_id,
            FeedbackHistory.user_id == current_user.id,
        )
        .first()
    )

    if not feedback:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found")

    if feedback.was_posted_to_jira:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Feedback already posted to Jira",
        )

    try:
        from api.issues.service import IssueService
        from src.feedback_writer import FeedbackWriter
        from src.pipeline import Feedback

        # Get Jira client
        issue_service = IssueService(db, current_user.id)
        jira_client = issue_service._get_jira_client()

        # Reconstruct Feedback object
        feedback_obj = Feedback(
            issue_key=feedback.issue_key,
            score=feedback.score,
            emoji=feedback.emoji,
            overall_assessment=feedback.overall_assessment,
            strengths=feedback.strengths,
            improvements=feedback.improvements,
            suggestions=feedback.suggestions,
            rubric_breakdown=feedback.rubric_breakdown,
            improved_ac=feedback.improved_ac,
            resources=feedback.resources or [],
        )

        # Post to Jira
        writer = FeedbackWriter(jira_client=jira_client, mode="comment")
        writer.deliver(feedback_obj, dry_run=False)

        # Update record
        feedback.was_posted_to_jira = True
        db.commit()

        issue_service.close()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to post to Jira: {e}",
        )


@router.delete("/{feedback_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feedback(
    feedback_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a feedback record."""
    feedback = (
        db.query(FeedbackHistory)
        .filter(
            FeedbackHistory.id == feedback_id,
            FeedbackHistory.user_id == current_user.id,
        )
        .first()
    )

    if not feedback:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found")

    db.delete(feedback)
    db.commit()
