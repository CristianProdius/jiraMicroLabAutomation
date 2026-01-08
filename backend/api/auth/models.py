"""Authentication database models."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from api.db.database import Base

if TYPE_CHECKING:
    from api.rubrics.models import UserRubricConfig
    from api.feedback.models import FeedbackHistory


class User(Base):
    """User account model."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    jira_credentials = relationship(
        "JiraCredential", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    telegram_link = relationship(
        "TelegramUserLink", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    rubric_configs = relationship(
        "UserRubricConfig", back_populates="user", cascade="all, delete-orphan"
    )
    feedback_history = relationship(
        "FeedbackHistory", back_populates="user", cascade="all, delete-orphan"
    )
    analysis_jobs = relationship(
        "AnalysisJob", back_populates="user", cascade="all, delete-orphan"
    )


class JiraCredential(Base):
    """Store user's Jira credentials (encrypted)."""

    __tablename__ = "jira_credentials"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    base_url = Column(String(500), nullable=False)
    email = Column(String(255), nullable=False)
    encrypted_api_token = Column(Text, nullable=False)  # Encrypted with Fernet
    is_valid = Column(Boolean, default=True)
    last_tested_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="jira_credentials")


class TelegramUserLink(Base):
    """Link Telegram chat to user account."""

    __tablename__ = "telegram_user_links"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    telegram_chat_id = Column(String(100), unique=True, nullable=False)
    telegram_username = Column(String(100), nullable=True)
    is_verified = Column(Boolean, default=False)
    verification_code = Column(String(50), nullable=True)
    verification_expires_at = Column(DateTime, nullable=True)
    notifications_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="telegram_link")


class RefreshToken(Base):
    """Store refresh tokens for JWT authentication."""

    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(500), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User")
