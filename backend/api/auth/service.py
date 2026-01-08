"""Authentication service layer."""

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from api.auth.models import User, JiraCredential, TelegramUserLink, RefreshToken
from api.auth.schemas import UserCreate, JiraCredentialsCreate
from api.auth.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    generate_verification_code,
    get_encryptor,
)
from api.config import get_settings
from api.rubrics.models import UserRubricConfig, RubricRule, AmbiguousTerm, DEFAULT_RUBRIC_RULES, DEFAULT_AMBIGUOUS_TERMS

settings = get_settings()


class AuthService:
    """Service for authentication operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by email address."""
        return self.db.query(User).filter(User.email == email).first()

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get a user by ID."""
        return self.db.query(User).filter(User.id == user_id).first()

    def create_user(self, user_data: UserCreate) -> User:
        """Create a new user with default rubric config."""
        # Create user
        user = User(
            email=user_data.email,
            hashed_password=get_password_hash(user_data.password),
            full_name=user_data.full_name,
        )
        self.db.add(user)
        self.db.flush()  # Get user ID before creating rubric config

        # Create default rubric configuration
        self._create_default_rubric_config(user.id)

        self.db.commit()
        self.db.refresh(user)
        return user

    def _create_default_rubric_config(self, user_id: int) -> UserRubricConfig:
        """Create default rubric configuration for a user."""
        config = UserRubricConfig(
            user_id=user_id,
            name="Default",
            is_default=True,
            min_description_words=settings.min_description_words,
            require_acceptance_criteria=settings.require_acceptance_criteria,
            allowed_labels=settings.allowed_labels.split(",") if settings.allowed_labels else None,
        )
        self.db.add(config)
        self.db.flush()

        # Add default rules
        for rule_data in DEFAULT_RUBRIC_RULES:
            rule = RubricRule(
                config_id=config.id,
                rule_id=rule_data["rule_id"],
                weight=rule_data["weight"],
                is_enabled=True,
                thresholds=rule_data.get("thresholds"),
            )
            self.db.add(rule)

        # Add default ambiguous terms
        for term in DEFAULT_AMBIGUOUS_TERMS:
            self.db.add(AmbiguousTerm(config_id=config.id, term=term))

        return config

    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate a user with email and password."""
        user = self.get_user_by_email(email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def create_tokens(self, user: User) -> dict:
        """Create access and refresh tokens for a user."""
        # Convert user.id to string for JWT sub claim (required by python-jose)
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})

        # Store refresh token in database
        expires_at = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
        token_record = RefreshToken(
            user_id=user.id,
            token=refresh_token,
            expires_at=expires_at,
        )
        self.db.add(token_record)
        self.db.commit()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
        }

    def refresh_access_token(self, refresh_token: str) -> Optional[dict]:
        """Refresh an access token using a refresh token."""
        from api.auth.security import decode_token

        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            return None

        # Check if refresh token exists and is not revoked
        token_record = (
            self.db.query(RefreshToken)
            .filter(RefreshToken.token == refresh_token, RefreshToken.revoked == False)
            .first()
        )
        if not token_record or token_record.expires_at < datetime.utcnow():
            return None

        # sub is stored as string in JWT, convert to int
        try:
            user_id = int(payload.get("sub"))
        except (TypeError, ValueError):
            return None

        user = self.get_user_by_id(user_id)
        if not user or not user.is_active:
            return None

        # Create new access token (keep same refresh token)
        access_token = create_access_token(data={"sub": str(user.id)})
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
        }

    def revoke_refresh_token(self, refresh_token: str) -> bool:
        """Revoke a refresh token (logout)."""
        token_record = (
            self.db.query(RefreshToken)
            .filter(RefreshToken.token == refresh_token)
            .first()
        )
        if token_record:
            token_record.revoked = True
            self.db.commit()
            return True
        return False

    def change_password(self, user: User, current_password: str, new_password: str) -> bool:
        """Change a user's password."""
        if not verify_password(current_password, user.hashed_password):
            return False
        user.hashed_password = get_password_hash(new_password)
        self.db.commit()
        return True


class JiraCredentialsService:
    """Service for managing Jira credentials."""

    def __init__(self, db: Session):
        self.db = db
        self.encryptor = get_encryptor()

    def get_credentials(self, user_id: int) -> Optional[JiraCredential]:
        """Get Jira credentials for a user."""
        return (
            self.db.query(JiraCredential)
            .filter(JiraCredential.user_id == user_id)
            .first()
        )

    def set_credentials(self, user_id: int, credentials: JiraCredentialsCreate) -> JiraCredential:
        """Set or update Jira credentials for a user."""
        existing = self.get_credentials(user_id)

        encrypted_token = self.encryptor.encrypt(credentials.api_token)

        if existing:
            existing.base_url = credentials.base_url
            existing.email = credentials.email
            existing.encrypted_api_token = encrypted_token
            existing.is_valid = True  # Reset validity
            existing.last_tested_at = None
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            new_creds = JiraCredential(
                user_id=user_id,
                base_url=credentials.base_url,
                email=credentials.email,
                encrypted_api_token=encrypted_token,
            )
            self.db.add(new_creds)
            self.db.commit()
            self.db.refresh(new_creds)
            return new_creds

    def delete_credentials(self, user_id: int) -> bool:
        """Delete Jira credentials for a user."""
        credentials = self.get_credentials(user_id)
        if credentials:
            self.db.delete(credentials)
            self.db.commit()
            return True
        return False

    def get_decrypted_token(self, credentials: JiraCredential) -> str:
        """Get the decrypted API token."""
        return self.encryptor.decrypt(credentials.encrypted_api_token)

    def mark_tested(self, credentials: JiraCredential, is_valid: bool) -> None:
        """Mark credentials as tested."""
        credentials.is_valid = is_valid
        credentials.last_tested_at = datetime.utcnow()
        self.db.commit()


class TelegramLinkService:
    """Service for managing Telegram account linking."""

    def __init__(self, db: Session):
        self.db = db

    def get_link(self, user_id: int) -> Optional[TelegramUserLink]:
        """Get Telegram link for a user."""
        return (
            self.db.query(TelegramUserLink)
            .filter(TelegramUserLink.user_id == user_id)
            .first()
        )

    def get_link_by_chat_id(self, chat_id: str) -> Optional[TelegramUserLink]:
        """Get Telegram link by chat ID."""
        return (
            self.db.query(TelegramUserLink)
            .filter(TelegramUserLink.telegram_chat_id == chat_id)
            .first()
        )

    def create_verification_code(self, user_id: int) -> tuple[str, datetime]:
        """Create or update verification code for linking."""
        code = generate_verification_code()
        expires_at = datetime.utcnow() + timedelta(minutes=10)

        link = self.get_link(user_id)
        if link:
            link.verification_code = code
            link.verification_expires_at = expires_at
            link.is_verified = False
        else:
            link = TelegramUserLink(
                user_id=user_id,
                telegram_chat_id="",  # Will be set when verified
                verification_code=code,
                verification_expires_at=expires_at,
            )
            self.db.add(link)

        self.db.commit()
        return code, expires_at

    def verify_code(self, code: str, chat_id: str, username: Optional[str] = None) -> Optional[TelegramUserLink]:
        """Verify a code and link the Telegram account."""
        link = (
            self.db.query(TelegramUserLink)
            .filter(
                TelegramUserLink.verification_code == code,
                TelegramUserLink.is_verified == False,
            )
            .first()
        )

        if not link:
            return None

        if link.verification_expires_at < datetime.utcnow():
            return None

        # Update link with Telegram info
        link.telegram_chat_id = chat_id
        link.telegram_username = username
        link.is_verified = True
        link.verification_code = None
        link.verification_expires_at = None
        self.db.commit()
        self.db.refresh(link)
        return link

    def unlink(self, user_id: int) -> bool:
        """Unlink Telegram account."""
        link = self.get_link(user_id)
        if link:
            self.db.delete(link)
            self.db.commit()
            return True
        return False

    def update_settings(self, user_id: int, notifications_enabled: bool) -> Optional[TelegramUserLink]:
        """Update Telegram notification settings."""
        link = self.get_link(user_id)
        if link and link.is_verified:
            link.notifications_enabled = notifications_enabled
            self.db.commit()
            self.db.refresh(link)
            return link
        return None
