"""Issues API routes."""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_current_user
from api.auth.models import User
from api.issues.schemas import (
    IssueSearchRequest,
    IssueResponse,
    IssueSearchResponse,
    AnalyzeSingleRequest,
    BatchAnalyzeRequest,
    JobStatusResponse,
    FeedbackResponse,
    RubricResultResponse,
)
from api.issues.service import IssueService, AnalysisService
from api.rubrics.models import DEFAULT_RUBRIC_RULES

router = APIRouter(prefix="/issues", tags=["Issues"])


# Rule ID to name mapping
RULE_NAMES = {rule["rule_id"]: rule["name"] for rule in DEFAULT_RUBRIC_RULES}


@router.post("/search", response_model=IssueSearchResponse)
async def search_issues(
    request: IssueSearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Search for Jira issues using JQL."""
    service = IssueService(db, current_user.id)
    try:
        issues = service.search_issues(
            jql=request.jql,
            max_results=request.max_results,
            fields=request.fields,
        )

        return IssueSearchResponse(
            issues=[
                IssueResponse(
                    key=issue.key,
                    summary=issue.summary,
                    description=issue.description,
                    labels=issue.labels,
                    assignee=issue.assignee,
                    issue_type=issue.issue_type,
                    estimate=issue.estimate,
                    status=issue.status,
                    content_hash=issue.content_hash(),
                )
                for issue in issues
            ],
            total=len(issues),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    finally:
        service.close()


@router.get("/{key}", response_model=IssueResponse)
async def get_issue(
    key: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single Jira issue by key."""
    service = IssueService(db, current_user.id)
    try:
        issue = service.get_issue(key)
        return IssueResponse(
            key=issue.key,
            summary=issue.summary,
            description=issue.description,
            labels=issue.labels,
            assignee=issue.assignee,
            issue_type=issue.issue_type,
            estimate=issue.estimate,
            status=issue.status,
            content_hash=issue.content_hash(),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Issue not found: {e}")
    finally:
        service.close()


@router.post("/{key}/analyze", response_model=FeedbackResponse)
async def analyze_issue(
    key: str,
    request: AnalyzeSingleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Analyze a single issue and get feedback."""
    analysis_service = AnalysisService(db, current_user.id)
    try:
        # Get the issue
        issue = analysis_service.issue_service.get_issue(key)

        # Analyze it
        feedback, rubric_results = analysis_service.analyze_issue(
            issue=issue,
            rubric_config_id=request.rubric_config_id,
        )

        # Save feedback history
        history = analysis_service.save_feedback(
            issue=issue,
            feedback=feedback,
            posted_to_jira=False,
        )

        # Post to Jira if requested
        if request.post_to_jira:
            try:
                from src.feedback_writer import FeedbackWriter
                from api.config import get_settings

                settings = get_settings()
                writer = FeedbackWriter(
                    jira_client=analysis_service.issue_service._get_jira_client(),
                    mode="comment",
                )
                writer.deliver(feedback, dry_run=False)
                history.was_posted_to_jira = True
                db.commit()
            except Exception as e:
                # Log but don't fail the request
                print(f"Failed to post comment to Jira: {e}")

        # Build response with rule names
        rubric_breakdown = [
            RubricResultResponse(
                rule_id=r.rule_id,
                rule_name=RULE_NAMES.get(r.rule_id, r.rule_id),
                score=r.score * 100,
                weight=r.weight,
                message=r.message,
                suggestion=r.suggestion,
            )
            for r in rubric_results
        ]

        return FeedbackResponse(
            id=history.id,
            issue_key=feedback.issue_key,
            score=feedback.score,
            emoji=feedback.emoji,
            overall_assessment=feedback.overall_assessment,
            strengths=feedback.strengths,
            improvements=feedback.improvements,
            suggestions=feedback.suggestions,
            rubric_breakdown=rubric_breakdown,
            improved_ac=feedback.improved_ac,
            resources=feedback.resources,
            was_posted_to_jira=history.was_posted_to_jira,
            created_at=history.created_at,
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    finally:
        analysis_service.close()


@router.post("/analyze-batch", response_model=JobStatusResponse)
async def analyze_batch(
    request: BatchAnalyzeRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Start a batch analysis job."""
    analysis_service = AnalysisService(db, current_user.id)

    # Create the job
    job = analysis_service.create_batch_job(
        jql=request.jql,
        max_issues=request.max_issues,
        rubric_config_id=request.rubric_config_id,
        dry_run=request.dry_run,
        post_to_jira=request.post_to_jira,
        send_telegram=request.send_telegram,
    )

    # Add background task to run analysis
    # TODO: Replace with proper task queue (Celery) for production
    background_tasks.add_task(
        run_batch_analysis,
        job_id=job.job_id,
        user_id=current_user.id,
    )

    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        total_issues=job.total_issues,
        processed_issues=job.processed_issues,
        failed_issues=job.failed_issues,
        progress_percent=0.0,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error_message=job.error_message,
    )


@router.get("/jobs", response_model=list[JobStatusResponse])
async def list_jobs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List recent analysis jobs."""
    analysis_service = AnalysisService(db, current_user.id)
    jobs = analysis_service.get_user_jobs()

    return [
        JobStatusResponse(
            job_id=job.job_id,
            status=job.status,
            total_issues=job.total_issues,
            processed_issues=job.processed_issues,
            failed_issues=job.failed_issues,
            progress_percent=(job.processed_issues / job.total_issues * 100) if job.total_issues > 0 else 0,
            current_issue_key=job.current_issue_key,
            average_score=job.average_score,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_message=job.error_message,
        )
        for job in jobs
    ]


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get status of an analysis job."""
    analysis_service = AnalysisService(db, current_user.id)
    job = analysis_service.get_job(job_id)

    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        total_issues=job.total_issues,
        processed_issues=job.processed_issues,
        failed_issues=job.failed_issues,
        progress_percent=(job.processed_issues / job.total_issues * 100) if job.total_issues > 0 else 0,
        current_issue_key=job.current_issue_key,
        average_score=job.average_score,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error_message=job.error_message,
    )


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel a running analysis job."""
    analysis_service = AnalysisService(db, current_user.id)
    job = analysis_service.get_job(job_id)

    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if job.status not in ["pending", "running"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job with status: {job.status}",
        )

    job.status = "cancelled"
    db.commit()


# Background task for batch analysis
async def run_batch_analysis(job_id: str, user_id: int):
    """Background task to run batch analysis with WebSocket updates."""
    from api.db.database import SessionLocal
    from datetime import datetime
    from api.websocket.manager import (
        emit_job_started,
        emit_job_progress,
        emit_issue_started,
        emit_issue_rubric_complete,
        emit_issue_complete,
        emit_issue_failed,
        emit_job_completed,
        emit_job_failed,
        emit_activity,
    )

    db = SessionLocal()
    start_time = datetime.utcnow()

    try:
        analysis_service = AnalysisService(db, user_id)
        job = analysis_service.get_job(job_id)

        if not job or job.status == "cancelled":
            return

        # Update job status
        job.status = "running"
        job.started_at = start_time
        db.commit()

        # Search for issues
        try:
            issues = analysis_service.issue_service.search_issues(
                jql=job.jql,
                max_results=job.max_issues,
            )
            job.total_issues = len(issues)
            db.commit()

            # Emit job started event
            await emit_job_started(
                job_id=job_id,
                user_id=user_id,
                jql=job.jql,
                total_issues=len(issues),
                dry_run=job.dry_run,
            )

        except Exception as e:
            job.status = "failed"
            job.error_message = f"Failed to search issues: {e}"
            job.completed_at = datetime.utcnow()
            db.commit()
            await emit_job_failed(job_id, user_id, str(e))
            return

        # Analyze each issue
        scores = []
        for i, issue in enumerate(issues):
            # Check if cancelled
            db.refresh(job)
            if job.status == "cancelled":
                await emit_activity(user_id, "cancelled", f"Job {job_id} was cancelled", "warning")
                return

            job.current_issue_key = issue.key
            db.commit()

            # Emit issue started
            await emit_issue_started(user_id, issue.key, issue.summary, job_id)

            try:
                feedback, rubric_results = analysis_service.analyze_issue(
                    issue=issue,
                    rubric_config_id=job.rubric_config_id,
                )

                # Emit rubric complete
                await emit_issue_rubric_complete(
                    user_id,
                    issue.key,
                    feedback.score,
                    feedback.rubric_breakdown,
                    job_id,
                )

                # Save feedback
                analysis_service.save_feedback(
                    issue=issue,
                    feedback=feedback,
                    posted_to_jira=False,
                )

                scores.append(feedback.score)
                job.processed_issues = i + 1

                # Post to Jira if requested and not dry run
                if job.post_to_jira and not job.dry_run:
                    try:
                        from src.feedback_writer import FeedbackWriter
                        writer = FeedbackWriter(
                            jira_client=analysis_service.issue_service._get_jira_client(),
                            mode="comment",
                        )
                        writer.deliver(feedback, dry_run=False)
                        await emit_activity(
                            user_id,
                            "comment",
                            f"Posted comment to {issue.key}",
                            "success",
                            issue.key,
                        )
                    except Exception as e:
                        await emit_activity(
                            user_id,
                            "error",
                            f"Failed to post comment to {issue.key}: {e}",
                            "error",
                            issue.key,
                        )

                db.commit()

                # Emit issue complete
                await emit_issue_complete(
                    user_id,
                    issue.key,
                    feedback.score,
                    feedback.emoji,
                    feedback.overall_assessment[:100],
                    job_id,
                )

                # Emit progress update
                await emit_job_progress(
                    job_id,
                    user_id,
                    issue.key,
                    i + 1,
                    len(issues),
                    job.failed_issues,
                )

            except Exception as e:
                job.failed_issues += 1
                db.commit()
                await emit_issue_failed(user_id, issue.key, str(e), job_id)
                # Continue with next issue

        # Update final statistics
        end_time = datetime.utcnow()
        job.status = "completed"
        job.completed_at = end_time
        job.current_issue_key = None
        if scores:
            job.average_score = sum(scores) / len(scores)
            job.lowest_score = min(scores)
            job.highest_score = max(scores)
        db.commit()

        # Emit job completed
        duration = (end_time - start_time).total_seconds()
        await emit_job_completed(
            job_id,
            user_id,
            job.processed_issues,
            job.failed_issues,
            job.average_score,
            duration,
        )

        # Send Telegram notification if requested
        if job.send_telegram:
            try:
                from api.telegram.service import send_job_summary
                await send_job_summary(user_id, job, db)
            except Exception as e:
                await emit_activity(
                    user_id,
                    "error",
                    f"Failed to send Telegram notification: {e}",
                    "error",
                )

    except Exception as e:
        try:
            job = db.query(AnalysisJob).filter(AnalysisJob.job_id == job_id).first()
            if job:
                job.status = "failed"
                job.error_message = str(e)
                job.completed_at = datetime.utcnow()
                db.commit()
            await emit_job_failed(job_id, user_id, str(e))
        except:
            pass
    finally:
        analysis_service.close()
        db.close()
