"""Telegram service functions."""

import secrets
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from api.db.database import SessionLocal
from api.auth.models import User, TelegramUserLink
from api.feedback.models import FeedbackHistory


async def generate_verification_code(user_id: int) -> dict:
    """Generate a verification code for Telegram linking."""
    db = SessionLocal()
    try:
        # Check if user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"success": False, "error": "User not found"}

        # Generate or update verification code
        link = (
            db.query(TelegramUserLink)
            .filter(TelegramUserLink.user_id == user_id)
            .first()
        )

        code = secrets.token_hex(3).upper()  # 6 character code

        if link:
            link.verification_code = code
            link.code_expires_at = datetime.utcnow() + timedelta(minutes=15)
        else:
            link = TelegramUserLink(
                user_id=user_id,
                verification_code=code,
                code_expires_at=datetime.utcnow() + timedelta(minutes=15),
            )
            db.add(link)

        db.commit()

        return {"success": True, "code": code, "expires_in_minutes": 15}
    finally:
        db.close()


async def verify_telegram_link(code: str, chat_id: str, username: Optional[str]) -> dict:
    """Verify a Telegram linking code and complete the link."""
    db = SessionLocal()
    try:
        # Find the link by verification code
        link = (
            db.query(TelegramUserLink)
            .filter(
                TelegramUserLink.verification_code == code,
                TelegramUserLink.code_expires_at > datetime.utcnow(),
            )
            .first()
        )

        if not link:
            return {"success": False, "error": "Invalid or expired code"}

        # Check if this chat_id is already linked to another account
        existing = (
            db.query(TelegramUserLink)
            .filter(
                TelegramUserLink.telegram_chat_id == chat_id,
                TelegramUserLink.id != link.id,
            )
            .first()
        )

        if existing:
            return {
                "success": False,
                "error": "This Telegram account is already linked to another user",
            }

        # Complete the link
        link.telegram_chat_id = chat_id
        link.telegram_username = username
        link.is_verified = True
        link.verification_code = None
        link.code_expires_at = None
        link.notifications_enabled = True

        db.commit()

        # Get user email for confirmation
        user = db.query(User).filter(User.id == link.user_id).first()

        return {"success": True, "email": user.email if user else "Unknown"}
    finally:
        db.close()


async def unlink_telegram(chat_id: str) -> dict:
    """Unlink a Telegram account."""
    db = SessionLocal()
    try:
        link = (
            db.query(TelegramUserLink)
            .filter(TelegramUserLink.telegram_chat_id == chat_id)
            .first()
        )

        if not link:
            return {"success": False, "error": "No linked account found"}

        # Clear the telegram info but keep the record
        link.telegram_chat_id = None
        link.telegram_username = None
        link.is_verified = False
        link.notifications_enabled = False

        db.commit()

        return {"success": True}
    finally:
        db.close()


async def get_telegram_status(chat_id: str) -> dict:
    """Get the status of a Telegram account link."""
    db = SessionLocal()
    try:
        link = (
            db.query(TelegramUserLink)
            .filter(TelegramUserLink.telegram_chat_id == chat_id)
            .first()
        )

        if not link or not link.is_verified:
            return {"is_linked": False}

        user = db.query(User).filter(User.id == link.user_id).first()

        # Count recent analyses
        recent_count = (
            db.query(FeedbackHistory)
            .filter(
                FeedbackHistory.user_id == link.user_id,
                FeedbackHistory.created_at > datetime.utcnow() - timedelta(days=7),
            )
            .count()
        )

        return {
            "is_linked": True,
            "email": user.email if user else "Unknown",
            "notifications_enabled": link.notifications_enabled,
            "recent_count": recent_count,
        }
    finally:
        db.close()


async def analyze_issue_for_telegram(chat_id: str, issue_key: str) -> dict:
    """Analyze an issue via Telegram command."""
    db = SessionLocal()
    try:
        # Get user from chat_id
        link = (
            db.query(TelegramUserLink)
            .filter(
                TelegramUserLink.telegram_chat_id == chat_id,
                TelegramUserLink.is_verified == True,
            )
            .first()
        )

        if not link:
            return {"success": False, "error": "Account not linked. Use /link first."}

        user = db.query(User).filter(User.id == link.user_id).first()
        if not user:
            return {"success": False, "error": "User not found"}

        # Import and use the analysis service
        from api.issues.service import JiraService, AnalysisService

        jira_service = JiraService(db, link.user_id)
        client = jira_service.get_client()

        if not client:
            return {
                "success": False,
                "error": "Jira not configured. Please set up Jira credentials in the web dashboard.",
            }

        # Fetch the issue
        try:
            issue = client.get_issue(issue_key)
        except Exception as e:
            return {"success": False, "error": f"Could not fetch issue: {str(e)}"}

        # Run analysis
        analysis_service = AnalysisService(db, link.user_id)
        feedback, rubric_results = analysis_service.analyze_issue(issue)

        # Determine emoji based on score
        if feedback.score >= 80:
            emoji = "🟢"
        elif feedback.score >= 60:
            emoji = "🟡"
        else:
            emoji = "🔴"

        return {
            "success": True,
            "feedback": {
                "score": feedback.score,
                "emoji": emoji,
                "assessment": feedback.overall_assessment,
                "strengths": feedback.strengths,
                "improvements": feedback.improvements,
            },
        }
    except Exception as e:
        return {"success": False, "error": f"Analysis failed: {str(e)}"}
    finally:
        db.close()


async def get_user_stats(chat_id: str) -> dict:
    """Get user statistics via Telegram."""
    db = SessionLocal()
    try:
        link = (
            db.query(TelegramUserLink)
            .filter(
                TelegramUserLink.telegram_chat_id == chat_id,
                TelegramUserLink.is_verified == True,
            )
            .first()
        )

        if not link:
            return {"success": False, "error": "Account not linked"}

        # Total analyzed
        total = (
            db.query(FeedbackHistory)
            .filter(FeedbackHistory.user_id == link.user_id)
            .count()
        )

        if total == 0:
            return {
                "success": True,
                "total_analyzed": 0,
                "average_score": 0,
                "this_week": 0,
                "below_70": 0,
            }

        # Average score
        avg_score = (
            db.query(func.avg(FeedbackHistory.score))
            .filter(FeedbackHistory.user_id == link.user_id)
            .scalar()
        ) or 0

        # This week
        week_ago = datetime.utcnow() - timedelta(days=7)
        this_week = (
            db.query(FeedbackHistory)
            .filter(
                FeedbackHistory.user_id == link.user_id,
                FeedbackHistory.created_at > week_ago,
            )
            .count()
        )

        # Below 70
        below_70 = (
            db.query(FeedbackHistory)
            .filter(
                FeedbackHistory.user_id == link.user_id,
                FeedbackHistory.score < 70,
            )
            .count()
        )

        return {
            "success": True,
            "total_analyzed": total,
            "average_score": float(avg_score),
            "this_week": this_week,
            "below_70": below_70,
        }
    finally:
        db.close()


async def update_telegram_settings(chat_id: str, notifications_enabled: bool) -> dict:
    """Update Telegram notification settings."""
    db = SessionLocal()
    try:
        link = (
            db.query(TelegramUserLink)
            .filter(
                TelegramUserLink.telegram_chat_id == chat_id,
                TelegramUserLink.is_verified == True,
            )
            .first()
        )

        if not link:
            return {"success": False, "error": "Account not linked"}

        link.notifications_enabled = notifications_enabled
        db.commit()

        return {"success": True}
    finally:
        db.close()


async def get_users_with_notifications_enabled() -> list[dict]:
    """Get all users who have Telegram notifications enabled."""
    db = SessionLocal()
    try:
        links = (
            db.query(TelegramUserLink)
            .filter(
                TelegramUserLink.is_verified == True,
                TelegramUserLink.notifications_enabled == True,
                TelegramUserLink.telegram_chat_id.isnot(None),
            )
            .all()
        )

        return [
            {
                "user_id": link.user_id,
                "chat_id": link.telegram_chat_id,
                "username": link.telegram_username,
            }
            for link in links
        ]
    finally:
        db.close()


def _escape_markdown(text: str) -> str:
    """Escape special characters for MarkdownV2."""
    if not text:
        return ""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text


def _get_score_emoji(score: float) -> str:
    """Get emoji based on score."""
    if score >= 80:
        return "🟢"
    elif score >= 60:
        return "🟡"
    else:
        return "🔴"


async def send_feedback_notification(user_id: int, issue_key: str, score: float, summary: str) -> bool:
    """Send a feedback notification to a user's Telegram if enabled."""
    db = SessionLocal()
    try:
        link = (
            db.query(TelegramUserLink)
            .filter(
                TelegramUserLink.user_id == user_id,
                TelegramUserLink.is_verified == True,
                TelegramUserLink.notifications_enabled == True,
                TelegramUserLink.telegram_chat_id.isnot(None),
            )
            .first()
        )

        if not link:
            return False

        from api.telegram.bot import get_bot

        bot = get_bot()

        emoji = _get_score_emoji(score)

        message = (
            f"{emoji} *New Feedback for `{_escape_markdown(issue_key)}`*\n\n"
            f"*Score:* {score:.0f}/100\n"
            f"*Summary:* {_escape_markdown(summary[:100])}{'\\.\\.\\.' if len(summary) > 100 else ''}\n\n"
            f"Use `/analyze {_escape_markdown(issue_key)}` for full details\\."
        )

        return await bot.send_notification(link.telegram_chat_id, message)
    finally:
        db.close()


async def send_job_summary(user_id: int, job, db: Session) -> bool:
    """Send a batch job completion summary to user's Telegram."""
    link = (
        db.query(TelegramUserLink)
        .filter(
            TelegramUserLink.user_id == user_id,
            TelegramUserLink.is_verified == True,
            TelegramUserLink.notifications_enabled == True,
            TelegramUserLink.telegram_chat_id.isnot(None),
        )
        .first()
    )

    if not link:
        return False

    from api.telegram.bot import get_bot

    bot = get_bot()

    # Determine overall status emoji
    if job.status == "completed":
        if job.failed_issues == 0:
            status_emoji = "✅"
            status_text = "Completed Successfully"
        else:
            status_emoji = "⚠️"
            status_text = "Completed with Errors"
    elif job.status == "failed":
        status_emoji = "❌"
        status_text = "Failed"
    else:
        status_emoji = "ℹ️"
        status_text = job.status.capitalize()

    # Score emoji
    avg_score = job.average_score or 0
    score_emoji = _get_score_emoji(avg_score)

    # Build message
    message = (
        f"{status_emoji} *Batch Analysis {status_text}*\n\n"
        f"📊 *Results Summary*\n"
        f"• Issues analyzed: *{job.processed_issues}*\n"
        f"• Failed: *{job.failed_issues}*\n"
    )

    if job.average_score is not None:
        message += f"• Average score: {score_emoji} *{job.average_score:.1f}*/100\n"

    if job.lowest_score is not None and job.highest_score is not None:
        message += f"• Score range: *{job.lowest_score:.0f}* \\- *{job.highest_score:.0f}*\n"

    # Add timing info
    if job.started_at and job.completed_at:
        duration = (job.completed_at - job.started_at).total_seconds()
        if duration < 60:
            duration_text = f"{duration:.0f} seconds"
        else:
            duration_text = f"{duration / 60:.1f} minutes"
        message += f"\n⏱️ Duration: {_escape_markdown(duration_text)}\n"

    message += "\nView detailed results in the web dashboard\\."

    return await bot.send_notification(link.telegram_chat_id, message)
