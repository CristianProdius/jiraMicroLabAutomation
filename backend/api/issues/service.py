"""Issue analysis service layer."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from api.auth.models import JiraCredential
from api.auth.service import JiraCredentialsService
from api.feedback.models import FeedbackHistory, AnalysisJob
from api.rubrics.models import UserRubricConfig, RubricRule, AmbiguousTerm
from src.config import JiraAuthConfig, RubricConfig
from src.jira_client import JiraClient, JiraIssue
from src.rubric import RubricEvaluator, RubricResult
from src.pipeline import FeedbackPipeline, Feedback


class JiraService:
    """Service for Jira client operations."""

    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id

    def get_client(self) -> Optional[JiraClient]:
        """Get a Jira client for the user if credentials are configured."""
        creds_service = JiraCredentialsService(self.db)
        credentials = creds_service.get_credentials(self.user_id)

        if not credentials:
            return None

        jira_config = JiraAuthConfig(
            method="pat",
            base_url=credentials.base_url,
            email=credentials.email,
            api_token=creds_service.get_decrypted_token(credentials),
        )
        return JiraClient(jira_config)


class IssueService:
    """Service for Jira issue operations."""

    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
        self._jira_client: Optional[JiraClient] = None

    def _get_jira_client(self) -> JiraClient:
        """Get or create Jira client for the user."""
        if self._jira_client:
            return self._jira_client

        creds_service = JiraCredentialsService(self.db)
        credentials = creds_service.get_credentials(self.user_id)

        if not credentials:
            raise ValueError("No Jira credentials configured")

        jira_config = JiraAuthConfig(
            method="pat",
            base_url=credentials.base_url,
            email=credentials.email,
            api_token=creds_service.get_decrypted_token(credentials),
        )
        self._jira_client = JiraClient(jira_config)
        return self._jira_client

    def search_issues(self, jql: str, max_results: int = 50, fields: Optional[list[str]] = None) -> list[JiraIssue]:
        """Search for issues using JQL."""
        client = self._get_jira_client()
        return client.search_issues(jql=jql, max_results=max_results, fields=fields)

    def get_issue(self, key: str) -> JiraIssue:
        """Get a single issue by key."""
        client = self._get_jira_client()
        return client.get_issue(key)

    def close(self):
        """Close the Jira client connection."""
        if self._jira_client:
            self._jira_client.close()
            self._jira_client = None


class RubricService:
    """Service for rubric configuration operations."""

    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id

    def get_default_config(self) -> Optional[UserRubricConfig]:
        """Get the user's default rubric configuration."""
        return (
            self.db.query(UserRubricConfig)
            .filter(
                UserRubricConfig.user_id == self.user_id,
                UserRubricConfig.is_default == True,
            )
            .first()
        )

    def get_config_by_id(self, config_id: int) -> Optional[UserRubricConfig]:
        """Get a specific rubric configuration."""
        return (
            self.db.query(UserRubricConfig)
            .filter(
                UserRubricConfig.id == config_id,
                UserRubricConfig.user_id == self.user_id,
            )
            .first()
        )

    def to_rubric_config(self, config: UserRubricConfig) -> RubricConfig:
        """Convert database config to RubricConfig for evaluation."""
        # Get ambiguous terms
        terms = [t.term for t in config.ambiguous_terms]

        return RubricConfig(
            min_description_words=config.min_description_words,
            require_acceptance_criteria=config.require_acceptance_criteria,
            allowed_labels=config.allowed_labels,
            ambiguous_terms=terms,
        )


class AnalysisService:
    """Service for issue analysis operations."""

    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
        self.issue_service = IssueService(db, user_id)
        self.rubric_service = RubricService(db, user_id)

    def analyze_issue(
        self,
        issue: JiraIssue,
        rubric_config_id: Optional[int] = None,
    ) -> tuple[Feedback, list[RubricResult]]:
        """Analyze a single issue and return feedback."""
        # Get rubric config
        if rubric_config_id:
            config = self.rubric_service.get_config_by_id(rubric_config_id)
        else:
            config = self.rubric_service.get_default_config()

        if not config:
            raise ValueError("No rubric configuration found")

        rubric_config = self.rubric_service.to_rubric_config(config)

        # Run rubric evaluation
        evaluator = RubricEvaluator(rubric_config)
        rubric_results = evaluator.evaluate(issue)
        score, breakdown = evaluator.calculate_final_score(rubric_results)

        # Create feedback (for now, rubric-only without LLM)
        # TODO: Integrate with FeedbackPipeline for LLM enhancement
        feedback = Feedback(
            issue_key=issue.key,
            score=score,
            emoji=self._get_score_emoji(score),
            overall_assessment=self._generate_assessment(score, rubric_results),
            strengths=[r.message for r in rubric_results if r.score >= 0.8],
            improvements=[r.message for r in rubric_results if r.score < 0.6],
            suggestions=[r.suggestion for r in rubric_results if r.suggestion],
            rubric_breakdown=breakdown,
            improved_ac=None,
            resources=[],
        )

        return feedback, rubric_results

    def _get_score_emoji(self, score: float) -> str:
        """Get emoji based on score."""
        if score >= 90:
            return "🌟"
        elif score >= 80:
            return "✅"
        elif score >= 70:
            return "👍"
        elif score >= 60:
            return "⚠️"
        elif score >= 50:
            return "🔧"
        else:
            return "❌"

    def _generate_assessment(self, score: float, results: list[RubricResult]) -> str:
        """Generate overall assessment text."""
        if score >= 90:
            return "Excellent issue! Well-defined with clear requirements."
        elif score >= 80:
            return "Good issue with minor improvements needed."
        elif score >= 70:
            return "Acceptable issue but could use more detail."
        elif score >= 60:
            return "Issue needs improvement in several areas."
        elif score >= 50:
            return "Issue requires significant improvements before development."
        else:
            return "Issue needs major rework to meet quality standards."

    def save_feedback(
        self,
        issue: JiraIssue,
        feedback: Feedback,
        posted_to_jira: bool = False,
    ) -> FeedbackHistory:
        """Save feedback to history with revision tracking."""
        # Convert rubric breakdown to the format expected
        rubric_breakdown = feedback.rubric_breakdown
        content_hash = issue.content_hash()

        # Check for previous feedback on this issue (revision detection)
        previous_feedback = (
            self.db.query(FeedbackHistory)
            .filter(
                FeedbackHistory.user_id == self.user_id,
                FeedbackHistory.issue_key == issue.key,
            )
            .order_by(FeedbackHistory.created_at.desc())
            .first()
        )

        # Determine revision info
        revision_number = 1
        previous_feedback_id = None

        if previous_feedback:
            # Only count as revision if content changed
            if previous_feedback.content_hash != content_hash:
                revision_number = previous_feedback.revision_number + 1
                previous_feedback_id = previous_feedback.id
            else:
                # Same content, still a new analysis but same revision
                revision_number = previous_feedback.revision_number
                previous_feedback_id = previous_feedback.id

        # Determine if passing (score >= 70)
        is_passing = feedback.score >= 70.0

        history = FeedbackHistory(
            user_id=self.user_id,
            issue_key=issue.key,
            content_hash=content_hash,
            score=feedback.score,
            emoji=feedback.emoji,
            overall_assessment=feedback.overall_assessment,
            strengths=feedback.strengths,
            improvements=feedback.improvements,
            suggestions=feedback.suggestions,
            rubric_breakdown=rubric_breakdown,
            improved_ac=feedback.improved_ac,
            resources=feedback.resources,
            issue_summary=issue.summary[:500] if issue.summary else None,
            issue_type=issue.issue_type,
            issue_status=issue.status,
            assignee=issue.assignee,
            labels=issue.labels,
            was_posted_to_jira=posted_to_jira,
            # Revision tracking
            previous_feedback_id=previous_feedback_id,
            revision_number=revision_number,
            is_passing=is_passing,
        )
        self.db.add(history)
        self.db.commit()
        self.db.refresh(history)
        return history

    def create_batch_job(
        self,
        jql: str,
        max_issues: int,
        rubric_config_id: Optional[int],
        dry_run: bool,
        post_to_jira: bool,
        send_telegram: bool,
    ) -> AnalysisJob:
        """Create a new batch analysis job."""
        job = AnalysisJob(
            job_id=str(uuid.uuid4()),
            user_id=self.user_id,
            jql=jql,
            max_issues=max_issues,
            rubric_config_id=rubric_config_id,
            dry_run=dry_run,
            post_to_jira=post_to_jira,
            send_telegram=send_telegram,
            status="pending",
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def get_job(self, job_id: str) -> Optional[AnalysisJob]:
        """Get a job by ID."""
        return (
            self.db.query(AnalysisJob)
            .filter(
                AnalysisJob.job_id == job_id,
                AnalysisJob.user_id == self.user_id,
            )
            .first()
        )

    def get_user_jobs(self, limit: int = 20) -> list[AnalysisJob]:
        """Get recent jobs for the user."""
        return (
            self.db.query(AnalysisJob)
            .filter(AnalysisJob.user_id == self.user_id)
            .order_by(AnalysisJob.created_at.desc())
            .limit(limit)
            .all()
        )

    def close(self):
        """Clean up resources."""
        self.issue_service.close()
