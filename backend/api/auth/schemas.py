"""Authentication Pydantic schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# ===================
# User Schemas
# ===================
class UserBase(BaseModel):
    """Base user schema."""

    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating a new user."""

    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")


class UserUpdate(BaseModel):
    """Schema for updating user profile."""

    full_name: Optional[str] = None
    email: Optional[EmailStr] = None


class UserResponse(UserBase):
    """Schema for user response."""

    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    has_jira_credentials: bool = False
    has_telegram_link: bool = False

    class Config:
        from_attributes = True


class UserInDB(UserBase):
    """Schema for user stored in database."""

    id: int
    hashed_password: str
    is_active: bool
    is_superuser: bool

    class Config:
        from_attributes = True


# ===================
# Authentication Schemas
# ===================
class LoginRequest(BaseModel):
    """Schema for login request."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Schema for token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class TokenRefreshRequest(BaseModel):
    """Schema for token refresh request."""

    refresh_token: str


class PasswordChangeRequest(BaseModel):
    """Schema for password change."""

    current_password: str
    new_password: str = Field(..., min_length=8)


# ===================
# Jira Credentials Schemas
# ===================
class JiraCredentialsCreate(BaseModel):
    """Schema for creating Jira credentials."""

    base_url: str = Field(..., pattern=r"^https?://")
    email: EmailStr
    api_token: str = Field(..., min_length=10)


class JiraCredentialsUpdate(BaseModel):
    """Schema for updating Jira credentials."""

    base_url: Optional[str] = Field(None, pattern=r"^https?://")
    email: Optional[EmailStr] = None
    api_token: Optional[str] = Field(None, min_length=10)


class JiraCredentialsStatus(BaseModel):
    """Schema for Jira credentials status (without sensitive data)."""

    is_configured: bool
    base_url: Optional[str] = None
    email: Optional[str] = None
    is_valid: Optional[bool] = None
    last_tested_at: Optional[datetime] = None


class JiraConnectionTest(BaseModel):
    """Schema for Jira connection test result."""

    success: bool
    message: str
    user_display_name: Optional[str] = None


# ===================
# Telegram Link Schemas
# ===================
class TelegramLinkRequest(BaseModel):
    """Schema for requesting Telegram link."""

    pass  # No parameters needed


class TelegramLinkResponse(BaseModel):
    """Schema for Telegram link response."""

    verification_code: str
    expires_in: int  # seconds
    bot_username: str
    instructions: str


class TelegramStatusResponse(BaseModel):
    """Schema for Telegram link status."""

    is_linked: bool
    telegram_username: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    notifications_enabled: bool = False
    linked_at: Optional[datetime] = None


class TelegramSettingsUpdate(BaseModel):
    """Schema for updating Telegram settings."""

    notifications_enabled: bool
