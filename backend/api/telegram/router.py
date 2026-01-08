"""Telegram API routes."""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel

from api.dependencies import get_db, get_current_user
from api.auth.models import User, TelegramUserLink
from api.telegram.bot import get_bot
from api.telegram.service import generate_verification_code

router = APIRouter(prefix="/telegram", tags=["Telegram"])


class GenerateCodeResponse(BaseModel):
    """Response for code generation."""

    code: str
    expires_in_minutes: int


class TelegramStatusResponse(BaseModel):
    """Response for Telegram status."""

    is_linked: bool
    telegram_username: str | None = None
    notifications_enabled: bool = False


class UpdateNotificationsRequest(BaseModel):
    """Request to update notification settings."""

    enabled: bool


@router.post("/generate-code", response_model=GenerateCodeResponse)
async def generate_link_code(
    current_user: User = Depends(get_current_user),
):
    """
    Generate a verification code for linking Telegram account.

    Use this code with the /link command in the Telegram bot.
    Code expires in 15 minutes.
    """
    result = await generate_verification_code(current_user.id)

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to generate code"),
        )

    return GenerateCodeResponse(
        code=result["code"],
        expires_in_minutes=result["expires_in_minutes"],
    )


@router.get("/status", response_model=TelegramStatusResponse)
async def get_link_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the current Telegram link status for the user."""
    link = (
        db.query(TelegramUserLink)
        .filter(
            TelegramUserLink.user_id == current_user.id,
            TelegramUserLink.is_verified == True,
        )
        .first()
    )

    if not link:
        return TelegramStatusResponse(is_linked=False)

    return TelegramStatusResponse(
        is_linked=True,
        telegram_username=link.telegram_username,
        notifications_enabled=link.notifications_enabled,
    )


@router.post("/notifications")
async def update_notifications(
    data: UpdateNotificationsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Enable or disable Telegram notifications."""
    link = (
        db.query(TelegramUserLink)
        .filter(
            TelegramUserLink.user_id == current_user.id,
            TelegramUserLink.is_verified == True,
        )
        .first()
    )

    if not link:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram account not linked",
        )

    link.notifications_enabled = data.enabled
    db.commit()

    return {"success": True, "notifications_enabled": data.enabled}


@router.delete("/unlink")
async def unlink_telegram(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Unlink the Telegram account from this user."""
    link = (
        db.query(TelegramUserLink)
        .filter(TelegramUserLink.user_id == current_user.id)
        .first()
    )

    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Telegram link found",
        )

    # Clear Telegram data but keep record
    link.telegram_chat_id = None
    link.telegram_username = None
    link.is_verified = False
    link.notifications_enabled = False

    db.commit()

    return {"success": True, "message": "Telegram account unlinked"}


@router.post("/webhook")
async def telegram_webhook(request: Request):
    """
    Webhook endpoint for Telegram bot updates.

    This endpoint receives updates from Telegram when users
    interact with the bot. Configure this URL in your Telegram
    bot settings via BotFather.
    """
    bot = get_bot()

    if not bot.application:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram bot not configured",
        )

    try:
        update_data = await request.json()
        await bot.process_update(update_data)
        return {"ok": True}
    except Exception as e:
        # Log error but return 200 to avoid Telegram retries
        print(f"Error processing Telegram update: {e}")
        return {"ok": True}


@router.get("/bot-info")
async def get_bot_info():
    """Get information about the Telegram bot (for setup instructions)."""
    bot = get_bot()

    if not bot.bot:
        return {
            "configured": False,
            "message": "Telegram bot token not configured. Set TELEGRAM_BOT_TOKEN in environment.",
        }

    try:
        bot_user = await bot.bot.get_me()
        return {
            "configured": True,
            "username": bot_user.username,
            "name": bot_user.first_name,
            "can_join_groups": bot_user.can_join_groups,
            "can_read_all_group_messages": bot_user.can_read_all_group_messages,
        }
    except Exception as e:
        return {
            "configured": True,
            "error": f"Could not fetch bot info: {str(e)}",
        }
