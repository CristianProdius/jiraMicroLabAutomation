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
    # Revision tracking
    IssueRevisionHistoryResponse,
    RevisionSummary,
    RevisionStatsResponse,
    # Student progress
    StudentSummaryItem,
    StudentProgressResponse,
    StudentsListResponse,
    SkillRadarData,
    MilestoneItem,
    # Grade export
    GradeExportRequest,
    GradeExportPreviewResponse,
    StudentGradeRecord,
    # Skill gap analysis
    SkillGapAnalysisResponse,
    SkillDetailResponse,
    WeakAreaItem,
    StudentGapItem,
    SkillTrendPoint,
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


# ============================================================
# Revision Tracking Endpoints
# ============================================================

# Rule names mapping for display
RULE_NAMES = {
    "title_clarity": "Title Clarity",
    "description_length": "Description Length",
    "acceptance_criteria": "Acceptance Criteria",
    "ambiguous_terms": "Ambiguous Terms",
    "estimate_present": "Estimate Present",
    "labels": "Labels",
    "scope_clarity": "Scope Clarity",
}


@router.get("/issue/{issue_key}/revisions", response_model=IssueRevisionHistoryResponse)
async def get_issue_revisions(
    issue_key: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get revision history for an issue."""
    feedbacks = (
        db.query(FeedbackHistory)
        .filter(
            FeedbackHistory.issue_key == issue_key.upper(),
            FeedbackHistory.user_id == current_user.id,
        )
        .order_by(FeedbackHistory.created_at.asc())
        .all()
    )

    if not feedbacks:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No feedback found for this issue")

    # Build revision list
    revisions = [
        RevisionSummary(
            id=f.id,
            revision_number=f.revision_number,
            score=f.score,
            emoji=f.emoji,
            is_passing=f.is_passing,
            content_hash=f.content_hash,
            created_at=f.created_at,
        )
        for f in feedbacks
    ]

    # Calculate revisions to pass
    revisions_to_pass = None
    for f in feedbacks:
        if f.is_passing:
            revisions_to_pass = f.revision_number
            break

    first_feedback = feedbacks[0]
    latest_feedback = feedbacks[-1]

    return IssueRevisionHistoryResponse(
        issue_key=issue_key.upper(),
        issue_summary=latest_feedback.issue_summary,
        revisions=revisions,
        total_revisions=latest_feedback.revision_number,
        revisions_to_pass=revisions_to_pass,
        first_score=first_feedback.score,
        latest_score=latest_feedback.score,
        score_improvement=latest_feedback.score - first_feedback.score,
    )


@router.get("/revisions/stats", response_model=RevisionStatsResponse)
async def get_revision_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get aggregate revision statistics."""
    # Get all feedbacks with revisions > 1
    all_feedbacks = (
        db.query(FeedbackHistory)
        .filter(FeedbackHistory.user_id == current_user.id)
        .all()
    )

    # Group by issue_key
    issues = defaultdict(list)
    for f in all_feedbacks:
        issues[f.issue_key].append(f)

    # Calculate stats
    issues_with_revisions = 0
    total_revisions = 0
    revisions_to_pass_list = []
    improvements = []

    for issue_key, feedbacks in issues.items():
        feedbacks.sort(key=lambda x: x.created_at)
        max_revision = max(f.revision_number for f in feedbacks)

        if max_revision > 1:
            issues_with_revisions += 1
            total_revisions += max_revision

            # Find revisions to pass
            for f in feedbacks:
                if f.is_passing:
                    revisions_to_pass_list.append(f.revision_number)
                    break

            # Calculate improvement
            first_score = feedbacks[0].score
            latest_score = feedbacks[-1].score
            if latest_score > first_score:
                improvements.append(latest_score - first_score)

    return RevisionStatsResponse(
        total_issues_with_revisions=issues_with_revisions,
        average_revisions_per_issue=round(total_revisions / issues_with_revisions, 1) if issues_with_revisions > 0 else 0,
        average_revisions_to_pass=round(sum(revisions_to_pass_list) / len(revisions_to_pass_list), 1) if revisions_to_pass_list else None,
        issues_improved_after_revision=len(improvements),
        average_score_improvement=round(sum(improvements) / len(improvements), 1) if improvements else 0,
    )


# ============================================================
# Student Progress Endpoints
# ============================================================


@router.get("/students", response_model=StudentsListResponse)
async def list_students(
    days: int = 90,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all students with summary stats."""
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)
    prev_start = start_date - timedelta(days=days)

    # Current period feedbacks
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

    # Aggregate by student
    current_by_student = defaultdict(list)
    for f in current_feedbacks:
        current_by_student[f.assignee].append(f)

    prev_by_student = defaultdict(list)
    for f in prev_feedbacks:
        prev_by_student[f.assignee].append(f)

    # Build student list
    students = []
    all_scores = []
    for assignee, feedbacks in current_by_student.items():
        scores = [f.score for f in feedbacks]
        all_scores.extend(scores)
        avg_score = sum(scores) / len(scores)
        passing_count = sum(1 for f in feedbacks if f.is_passing)
        passing_rate = passing_count / len(feedbacks) * 100

        # Calculate trend
        prev_scores = [f.score for f in prev_by_student.get(assignee, [])]
        prev_avg = sum(prev_scores) / len(prev_scores) if prev_scores else avg_score
        trend = round(avg_score - prev_avg, 1)

        # Latest activity
        latest = max(f.created_at for f in feedbacks)

        students.append(
            StudentSummaryItem(
                assignee=assignee,
                total_issues=len(feedbacks),
                average_score=round(avg_score, 1),
                passing_rate=round(passing_rate, 1),
                trend=trend,
                latest_activity=latest,
            )
        )

    # Sort by average score descending
    students.sort(key=lambda x: -x.average_score)

    return StudentsListResponse(
        students=students,
        total_students=len(students),
        class_average_score=round(sum(all_scores) / len(all_scores), 1) if all_scores else 0,
    )


@router.get("/student/{assignee}", response_model=StudentProgressResponse)
async def get_student_progress(
    assignee: str,
    days: int = 90,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get detailed progress for a specific student."""
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)

    # Get student feedbacks
    feedbacks = (
        db.query(FeedbackHistory)
        .filter(
            FeedbackHistory.user_id == current_user.id,
            FeedbackHistory.assignee == assignee,
            FeedbackHistory.created_at >= start_date,
        )
        .order_by(FeedbackHistory.created_at.asc())
        .all()
    )

    if not feedbacks:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No feedback found for this student")

    # Get class data for comparison
    all_feedbacks = (
        db.query(FeedbackHistory)
        .filter(
            FeedbackHistory.user_id == current_user.id,
            FeedbackHistory.created_at >= start_date,
        )
        .all()
    )

    # Calculate basic stats
    scores = [f.score for f in feedbacks]
    avg_score = sum(scores) / len(scores)
    passing_count = sum(1 for f in feedbacks if f.is_passing)
    passing_rate = passing_count / len(feedbacks) * 100

    # Score trend (daily)
    daily_data = defaultdict(list)
    for f in feedbacks:
        date_str = f.created_at.strftime("%Y-%m-%d")
        daily_data[date_str].append(f.score)

    score_trend = []
    current = start_date
    while current <= now:
        date_str = current.strftime("%Y-%m-%d")
        day_scores = daily_data.get(date_str, [])
        score_trend.append(
            ScoreTrendItem(
                date=date_str,
                average_score=round(sum(day_scores) / len(day_scores), 1) if day_scores else 0,
                count=len(day_scores),
            )
        )
        current += timedelta(days=1)

    # Skill breakdown from rubric_breakdown
    skill_scores = defaultdict(list)
    for f in feedbacks:
        if f.rubric_breakdown:
            for rule_id, data in f.rubric_breakdown.items():
                # Score is 0-1 in breakdown, convert to 0-100
                score = data.get("score", 0) if isinstance(data, dict) else data
                if isinstance(score, (int, float)):
                    skill_scores[rule_id].append(score * 100 if score <= 1 else score)

    skill_breakdown = {k: round(sum(v) / len(v), 1) for k, v in skill_scores.items()}

    # Class averages for comparison
    class_skill_scores = defaultdict(list)
    for f in all_feedbacks:
        if f.rubric_breakdown:
            for rule_id, data in f.rubric_breakdown.items():
                score = data.get("score", 0) if isinstance(data, dict) else data
                if isinstance(score, (int, float)):
                    class_skill_scores[rule_id].append(score * 100 if score <= 1 else score)

    class_averages = {k: round(sum(v) / len(v), 1) for k, v in class_skill_scores.items()}

    # Class comparison (difference from class avg)
    class_comparison = {}
    for rule_id in skill_breakdown:
        student_avg = skill_breakdown.get(rule_id, 0)
        class_avg = class_averages.get(rule_id, 0)
        class_comparison[rule_id] = round(student_avg - class_avg, 1)

    # Detect milestones
    milestones = _detect_milestones(feedbacks)

    # Recent feedbacks
    recent = feedbacks[-10:][::-1]  # Last 10, newest first
    recent_feedbacks = [
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
        for f in recent
    ]

    return StudentProgressResponse(
        assignee=assignee,
        total_issues=len(feedbacks),
        average_score=round(avg_score, 1),
        passing_rate=round(passing_rate, 1),
        score_trend=score_trend,
        skill_breakdown=skill_breakdown,
        class_comparison=class_comparison,
        milestones=milestones,
        recent_feedbacks=recent_feedbacks,
    )


@router.get("/student/{assignee}/skill-radar", response_model=SkillRadarData)
async def get_student_skill_radar(
    assignee: str,
    days: int = 90,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get radar chart data for student skills vs class average."""
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)

    # Get all feedbacks
    all_feedbacks = (
        db.query(FeedbackHistory)
        .filter(
            FeedbackHistory.user_id == current_user.id,
            FeedbackHistory.created_at >= start_date,
        )
        .all()
    )

    student_feedbacks = [f for f in all_feedbacks if f.assignee == assignee]

    if not student_feedbacks:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No feedback found for this student")

    # Calculate skill scores
    student_skills = defaultdict(list)
    class_skills = defaultdict(list)

    for f in all_feedbacks:
        if f.rubric_breakdown:
            for rule_id, data in f.rubric_breakdown.items():
                score = data.get("score", 0) if isinstance(data, dict) else data
                if isinstance(score, (int, float)):
                    normalized = score * 100 if score <= 1 else score
                    class_skills[rule_id].append(normalized)
                    if f.assignee == assignee:
                        student_skills[rule_id].append(normalized)

    # Build radar data
    skill_ids = list(RULE_NAMES.keys())
    skills = [RULE_NAMES.get(sid, sid) for sid in skill_ids]
    student_scores = [round(sum(student_skills.get(sid, [0])) / max(len(student_skills.get(sid, [1])), 1), 1) for sid in skill_ids]
    class_scores = [round(sum(class_skills.get(sid, [0])) / max(len(class_skills.get(sid, [1])), 1), 1) for sid in skill_ids]

    return SkillRadarData(
        skills=skills,
        skill_ids=skill_ids,
        student_scores=student_scores,
        class_average_scores=class_scores,
    )


def _detect_milestones(feedbacks: list[FeedbackHistory]) -> list[MilestoneItem]:
    """Detect achievement milestones for a student."""
    milestones = []
    feedbacks_sorted = sorted(feedbacks, key=lambda x: x.created_at)

    # First passing score
    first_passing = next((f for f in feedbacks_sorted if f.is_passing), None)
    if first_passing:
        milestones.append(
            MilestoneItem(
                type="first_passing",
                title="First Passing Score",
                description=f"Achieved first passing score of {first_passing.score:.0f}",
                achieved_at=first_passing.created_at,
                issue_key=first_passing.issue_key,
            )
        )

    # Perfect score (90+)
    perfect = next((f for f in feedbacks_sorted if f.score >= 90), None)
    if perfect:
        milestones.append(
            MilestoneItem(
                type="perfect_score",
                title="Excellent Work",
                description=f"Achieved score of {perfect.score:.0f} - Excellent!",
                achieved_at=perfect.created_at,
                issue_key=perfect.issue_key,
            )
        )

    # Streak (3+ consecutive passing)
    streak = 0
    max_streak = 0
    streak_end = None
    for f in feedbacks_sorted:
        if f.is_passing:
            streak += 1
            if streak > max_streak:
                max_streak = streak
                streak_end = f
        else:
            streak = 0

    if max_streak >= 3:
        milestones.append(
            MilestoneItem(
                type="streak",
                title=f"{max_streak} Issue Streak",
                description=f"Maintained passing scores for {max_streak} consecutive issues",
                achieved_at=streak_end.created_at,
                issue_key=streak_end.issue_key,
            )
        )

    # Significant improvement (20+ point jump)
    for i in range(1, len(feedbacks_sorted)):
        improvement = feedbacks_sorted[i].score - feedbacks_sorted[i - 1].score
        if improvement >= 20:
            milestones.append(
                MilestoneItem(
                    type="improvement",
                    title="Big Improvement",
                    description=f"Improved by {improvement:.0f} points from previous issue",
                    achieved_at=feedbacks_sorted[i].created_at,
                    issue_key=feedbacks_sorted[i].issue_key,
                )
            )
            break  # Only record first big improvement

    return milestones


# ============================================================
# Grade Export Endpoints
# ============================================================

from fastapi.responses import StreamingResponse
import csv
import io


@router.post("/export/grades/preview", response_model=GradeExportPreviewResponse)
async def preview_grade_export(
    request: GradeExportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Preview grade export data before downloading."""
    records, class_avg, date_range = _calculate_grades(db, current_user.id, request)

    return GradeExportPreviewResponse(
        records=records,
        total_students=len(records),
        class_average=class_avg,
        date_range=date_range,
    )


@router.post("/export/grades")
async def export_grades(
    request: GradeExportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export student grades as CSV."""
    records, class_avg, date_range = _calculate_grades(db, current_user.id, request)

    # Generate CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Student Name", "Issues Analyzed", "Average Score", "Trend", "Letter Grade", "Passing Rate"])

    for record in records:
        writer.writerow([
            record.student_name,
            record.issue_count,
            f"{record.average_score:.1f}",
            f"{record.trend:+.1f}",
            record.letter_grade,
            f"{record.passing_rate:.1f}%",
        ])

    # Add summary row
    writer.writerow([])
    writer.writerow(["Class Average", "", f"{class_avg:.1f}", "", "", ""])
    writer.writerow(["Date Range", date_range, "", "", "", ""])

    output.seek(0)
    filename = f"grades_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


def _calculate_grades(db: Session, user_id: int, request: GradeExportRequest) -> tuple[list[StudentGradeRecord], float, str]:
    """Calculate grades for all students."""
    # Default grade mapping
    grade_mapping = request.grade_mapping or {
        "A": [90, 100],
        "B": [80, 89.99],
        "C": [70, 79.99],
        "D": [60, 69.99],
        "F": [0, 59.99],
    }

    # Build query
    query = db.query(FeedbackHistory).filter(
        FeedbackHistory.user_id == user_id,
        FeedbackHistory.assignee.isnot(None),
    )

    if request.from_date:
        query = query.filter(FeedbackHistory.created_at >= request.from_date)
    if request.to_date:
        query = query.filter(FeedbackHistory.created_at <= request.to_date)

    feedbacks = query.all()

    # Calculate date range string
    if feedbacks:
        dates = [f.created_at for f in feedbacks]
        date_range = f"{min(dates).strftime('%Y-%m-%d')} to {max(dates).strftime('%Y-%m-%d')}"
    else:
        date_range = "No data"

    # Aggregate by student
    students = defaultdict(list)
    for f in feedbacks:
        students[f.assignee].append(f)

    # Calculate grades
    records = []
    all_scores = []

    for assignee, student_feedbacks in students.items():
        scores = [f.score for f in student_feedbacks]
        all_scores.extend(scores)
        avg_score = sum(scores) / len(scores)
        passing_count = sum(1 for f in student_feedbacks if f.is_passing)
        passing_rate = passing_count / len(student_feedbacks) * 100

        # Calculate trend (first half vs second half)
        sorted_feedbacks = sorted(student_feedbacks, key=lambda x: x.created_at)
        mid = len(sorted_feedbacks) // 2
        if mid > 0:
            first_half = sum(f.score for f in sorted_feedbacks[:mid]) / mid
            second_half = sum(f.score for f in sorted_feedbacks[mid:]) / len(sorted_feedbacks[mid:])
            trend = second_half - first_half
        else:
            trend = 0

        # Determine letter grade
        letter_grade = "F"
        for grade, (low, high) in grade_mapping.items():
            if low <= avg_score <= high:
                letter_grade = grade
                break

        records.append(
            StudentGradeRecord(
                student_name=assignee,
                issue_count=len(student_feedbacks),
                average_score=round(avg_score, 1),
                trend=round(trend, 1),
                letter_grade=letter_grade,
                passing_rate=round(passing_rate, 1),
            )
        )

    # Sort by name
    records.sort(key=lambda x: x.student_name)

    class_avg = sum(all_scores) / len(all_scores) if all_scores else 0

    return records, round(class_avg, 1), date_range


# ============================================================
# Skill Gap Analysis Endpoints
# ============================================================


@router.get("/skills/analysis", response_model=SkillGapAnalysisResponse)
async def get_skill_gap_analysis(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get class-wide skill gap analysis."""
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)
    prev_start = start_date - timedelta(days=days)

    # Get current period feedbacks
    feedbacks = (
        db.query(FeedbackHistory)
        .filter(
            FeedbackHistory.user_id == current_user.id,
            FeedbackHistory.created_at >= start_date,
        )
        .all()
    )

    # Get previous period for trends
    prev_feedbacks = (
        db.query(FeedbackHistory)
        .filter(
            FeedbackHistory.user_id == current_user.id,
            FeedbackHistory.created_at >= prev_start,
            FeedbackHistory.created_at < start_date,
        )
        .all()
    )

    # Aggregate skill scores
    skill_scores = defaultdict(list)
    skill_by_date = defaultdict(lambda: defaultdict(list))
    skill_by_student = defaultdict(lambda: defaultdict(list))

    for f in feedbacks:
        if f.rubric_breakdown:
            date_str = f.created_at.strftime("%Y-%m-%d")
            for rule_id, data in f.rubric_breakdown.items():
                score = data.get("score", 0) if isinstance(data, dict) else data
                if isinstance(score, (int, float)):
                    normalized = score * 100 if score <= 1 else score
                    skill_scores[rule_id].append(normalized)
                    skill_by_date[rule_id][date_str].append(normalized)
                    if f.assignee:
                        skill_by_student[f.assignee][rule_id].append(normalized)

    # Previous period scores for trend
    prev_skill_scores = defaultdict(list)
    for f in prev_feedbacks:
        if f.rubric_breakdown:
            for rule_id, data in f.rubric_breakdown.items():
                score = data.get("score", 0) if isinstance(data, dict) else data
                if isinstance(score, (int, float)):
                    normalized = score * 100 if score <= 1 else score
                    prev_skill_scores[rule_id].append(normalized)

    # Calculate overall stats
    overall_stats = {k: round(sum(v) / len(v), 1) for k, v in skill_scores.items()}

    # Build time series
    time_series = {}
    for rule_id in skill_scores:
        series = []
        current = start_date
        while current <= now:
            date_str = current.strftime("%Y-%m-%d")
            day_scores = skill_by_date[rule_id].get(date_str, [])
            series.append(
                SkillTrendPoint(
                    date=date_str,
                    average_score=round(sum(day_scores) / len(day_scores), 1) if day_scores else 0,
                    sample_size=len(day_scores),
                )
            )
            current += timedelta(days=1)
        time_series[rule_id] = series

    # Identify weak and strong areas
    areas = []
    for rule_id, scores in skill_scores.items():
        avg = sum(scores) / len(scores)
        struggling = sum(1 for s in scores if s < 70)
        prev_avg = sum(prev_skill_scores.get(rule_id, [avg])) / max(len(prev_skill_scores.get(rule_id, [1])), 1)
        trend = avg - prev_avg

        areas.append(
            WeakAreaItem(
                rule_id=rule_id,
                rule_name=RULE_NAMES.get(rule_id, rule_id),
                average_score=round(avg, 1),
                students_struggling=struggling,
                improvement_trend=round(trend, 1),
            )
        )

    # Sort for weak/strong
    areas.sort(key=lambda x: x.average_score)
    weak_areas = areas[:3]  # Bottom 3
    strong_areas = sorted(areas, key=lambda x: -x.average_score)[:3]  # Top 3

    # Per-student gaps
    student_gaps = []
    class_avgs = {k: sum(v) / len(v) for k, v in skill_scores.items()}

    for assignee, skills in skill_by_student.items():
        gaps = []
        biggest_gap = ""
        biggest_gap_amount = 0

        for rule_id, scores in skills.items():
            student_avg = sum(scores) / len(scores)
            class_avg = class_avgs.get(rule_id, 0)
            gap = class_avg - student_avg

            if gap > 5:  # More than 5 points below class avg
                gaps.append(rule_id)
                if gap > biggest_gap_amount:
                    biggest_gap_amount = gap
                    biggest_gap = rule_id

        if gaps:
            student_gaps.append(
                StudentGapItem(
                    assignee=assignee,
                    skill_gaps=gaps,
                    biggest_gap_rule=RULE_NAMES.get(biggest_gap, biggest_gap),
                    biggest_gap_amount=round(biggest_gap_amount, 1),
                )
            )

    # Sort by biggest gap
    student_gaps.sort(key=lambda x: -x.biggest_gap_amount)

    return SkillGapAnalysisResponse(
        overall_stats=overall_stats,
        rule_names=RULE_NAMES,
        time_series=time_series,
        weak_areas=weak_areas,
        strong_areas=strong_areas,
        student_gaps=student_gaps[:10],  # Top 10 students with gaps
    )


@router.get("/skills/{rule_id}", response_model=SkillDetailResponse)
async def get_skill_details(
    rule_id: str,
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get detailed analysis for a specific skill."""
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

    # Extract scores for this rule
    scores = []
    scores_by_date = defaultdict(list)
    scores_by_student = defaultdict(list)

    for f in feedbacks:
        if f.rubric_breakdown and rule_id in f.rubric_breakdown:
            data = f.rubric_breakdown[rule_id]
            score = data.get("score", 0) if isinstance(data, dict) else data
            if isinstance(score, (int, float)):
                normalized = score * 100 if score <= 1 else score
                scores.append(normalized)
                scores_by_date[f.created_at.strftime("%Y-%m-%d")].append(normalized)
                if f.assignee:
                    scores_by_student[f.assignee].append(normalized)

    if not scores:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No data found for this skill")

    # Class average
    class_average = sum(scores) / len(scores)

    # Trend data
    trend_data = []
    current = start_date
    while current <= now:
        date_str = current.strftime("%Y-%m-%d")
        day_scores = scores_by_date.get(date_str, [])
        trend_data.append(
            SkillTrendPoint(
                date=date_str,
                average_score=round(sum(day_scores) / len(day_scores), 1) if day_scores else 0,
                sample_size=len(day_scores),
            )
        )
        current += timedelta(days=1)

    # Score distribution
    distribution = defaultdict(int)
    for s in scores:
        if s >= 90:
            distribution["90-100"] += 1
        elif s >= 80:
            distribution["80-89"] += 1
        elif s >= 70:
            distribution["70-79"] += 1
        elif s >= 60:
            distribution["60-69"] += 1
        elif s >= 50:
            distribution["50-59"] += 1
        else:
            distribution["0-49"] += 1

    # Students by performance
    excellent = []
    good = []
    struggling = []

    for assignee, student_scores in scores_by_student.items():
        avg = sum(student_scores) / len(student_scores)
        if avg >= 90:
            excellent.append(assignee)
        elif avg >= 70:
            good.append(assignee)
        else:
            struggling.append(assignee)

    students_by_performance = {
        "excellent": excellent,
        "good": good,
        "struggling": struggling,
    }

    # Improvement suggestions based on rule
    suggestions = _get_skill_suggestions(rule_id)

    return SkillDetailResponse(
        rule_id=rule_id,
        rule_name=RULE_NAMES.get(rule_id, rule_id),
        class_average=round(class_average, 1),
        trend_data=trend_data,
        score_distribution=dict(distribution),
        students_by_performance=students_by_performance,
        improvement_suggestions=suggestions,
    )


def _get_skill_suggestions(rule_id: str) -> list[str]:
    """Get improvement suggestions for a skill."""
    suggestions = {
        "title_clarity": [
            "Use action verbs at the start of titles (Add, Fix, Create, Update, Remove)",
            "Keep titles concise (10-100 characters)",
            "Avoid filler words like 'just', 'maybe', 'perhaps'",
        ],
        "description_length": [
            "Provide context about why this issue is needed",
            "Include technical details and constraints",
            "Describe the expected behavior or outcome",
        ],
        "acceptance_criteria": [
            "Use Given/When/Then format for testable criteria",
            "Include specific measurable outcomes",
            "Add checkboxes for each acceptance criterion",
        ],
        "ambiguous_terms": [
            "Replace 'optimize' with specific performance targets",
            "Replace 'ASAP' with actual deadlines",
            "Be specific about what 'improve' or 'enhance' means",
        ],
        "estimate_present": [
            "Add story points based on complexity",
            "Use planning poker for team estimates",
            "Break down large issues if estimate is too high",
        ],
        "labels": [
            "Add appropriate labels for categorization",
            "Use consistent label naming conventions",
            "Include priority and type labels",
        ],
        "scope_clarity": [
            "Clearly define what is in scope and out of scope",
            "List any dependencies on other issues",
            "Specify any technical constraints or limitations",
        ],
    }
    return suggestions.get(rule_id, ["Review rubric guidelines for this criterion"])
