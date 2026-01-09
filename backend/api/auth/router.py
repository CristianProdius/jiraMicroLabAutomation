"""Authentication API routes."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_current_user
from api.auth.models import User
from api.auth.schemas import (
    UserCreate,
    UserResponse,
    UserUpdate,
    LoginRequest,
    TokenResponse,
    TokenRefreshRequest,
    PasswordChangeRequest,
    JiraCredentialsCreate,
    JiraCredentialsStatus,
    JiraConnectionTest,
    TelegramLinkResponse,
    TelegramStatusResponse,
    TelegramSettingsUpdate,
)
from api.auth.service import AuthService, JiraCredentialsService, TelegramLinkService
from api.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["Authentication"])

# Cookie settings
COOKIE_SECURE = False  # Set to True in production with HTTPS
COOKIE_SAMESITE = "lax"
COOKIE_HTTPONLY = True
ACCESS_TOKEN_MAX_AGE = settings.access_token_expire_minutes * 60  # seconds
REFRESH_TOKEN_MAX_AGE = settings.refresh_token_expire_days * 24 * 60 * 60  # seconds


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Set HTTP-only authentication cookies."""
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=ACCESS_TOKEN_MAX_AGE,
        httponly=COOKIE_HTTPONLY,
        samesite=COOKIE_SAMESITE,
        secure=COOKIE_SECURE,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=REFRESH_TOKEN_MAX_AGE,
        httponly=COOKIE_HTTPONLY,
        samesite=COOKIE_SAMESITE,
        secure=COOKIE_SECURE,
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    """Clear authentication cookies."""
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/")


# ===================
# WebSocket Token
# ===================
@router.get("/ws-token")
async def get_ws_token(current_user: User = Depends(get_current_user)):
    """
    Get a short-lived token for WebSocket authentication.
    This allows cookie-authenticated users to connect to WebSockets.
    """
    from datetime import timedelta
    from api.auth.security import create_access_token

    # Create a short-lived token (5 minutes) for WebSocket connection
    # Convert user.id to string for JWT sub claim (required by python-jose)
    token = create_access_token(
        data={"sub": str(current_user.id)},
        expires_delta=timedelta(minutes=5),
    )
    return {"token": token}


# ===================
# User Registration & Login
# ===================
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    service = AuthService(db)

    # Check if user exists
    if service.get_user_by_email(user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = service.create_user(user_data)
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        created_at=user.created_at,
        has_jira_credentials=False,
        has_telegram_link=False,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Login and get JWT tokens."""
    service = AuthService(db)

    user = service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    tokens = service.create_tokens(user)

    # Set HTTP-only cookies for browser authentication
    set_auth_cookies(response, tokens["access_token"], tokens["refresh_token"])

    return tokens


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    response: Response,
    request: TokenRefreshRequest,
    db: Session = Depends(get_db),
):
    """Refresh access token using refresh token."""
    service = AuthService(db)

    tokens = service.refresh_access_token(request.refresh_token)
    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Update cookies with new tokens
    set_auth_cookies(response, tokens["access_token"], tokens["refresh_token"])

    return tokens


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    db: Session = Depends(get_db),
):
    """Logout by clearing authentication cookies."""
    # Clear authentication cookies
    clear_auth_cookies(response)


# ===================
# Current User
# ===================
@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get current user profile."""
    jira_service = JiraCredentialsService(db)
    telegram_service = TelegramLinkService(db)

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        created_at=current_user.created_at,
        has_jira_credentials=jira_service.get_credentials(current_user.id) is not None,
        has_telegram_link=telegram_service.get_link(current_user.id) is not None
        and telegram_service.get_link(current_user.id).is_verified,
    )


@router.put("/me", response_model=UserResponse)
async def update_me(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update current user profile."""
    if user_data.full_name is not None:
        current_user.full_name = user_data.full_name
    if user_data.email is not None:
        # Check if email is taken
        service = AuthService(db)
        existing = service.get_user_by_email(user_data.email)
        if existing and existing.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already taken",
            )
        current_user.email = user_data.email

    db.commit()
    db.refresh(current_user)

    jira_service = JiraCredentialsService(db)
    telegram_service = TelegramLinkService(db)

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        created_at=current_user.created_at,
        has_jira_credentials=jira_service.get_credentials(current_user.id) is not None,
        has_telegram_link=telegram_service.get_link(current_user.id) is not None,
    )


@router.put("/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change current user's password."""
    service = AuthService(db)
    if not service.change_password(current_user, request.current_password, request.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )


# ===================
# Jira Credentials
# ===================
@router.get("/jira/credentials", response_model=JiraCredentialsStatus)
async def get_jira_credentials(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get Jira credentials status (not the actual credentials)."""
    service = JiraCredentialsService(db)
    credentials = service.get_credentials(current_user.id)

    if not credentials:
        return JiraCredentialsStatus(is_configured=False)

    return JiraCredentialsStatus(
        is_configured=True,
        base_url=credentials.base_url,
        email=credentials.email,
        is_valid=credentials.is_valid,
        last_tested_at=credentials.last_tested_at,
    )


@router.post("/jira/credentials", response_model=JiraCredentialsStatus)
async def set_jira_credentials(
    credentials: JiraCredentialsCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Set Jira credentials."""
    service = JiraCredentialsService(db)
    creds = service.set_credentials(current_user.id, credentials)

    return JiraCredentialsStatus(
        is_configured=True,
        base_url=creds.base_url,
        email=creds.email,
        is_valid=creds.is_valid,
        last_tested_at=creds.last_tested_at,
    )


@router.delete("/jira/credentials", status_code=status.HTTP_204_NO_CONTENT)
async def delete_jira_credentials(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete Jira credentials."""
    service = JiraCredentialsService(db)
    if not service.delete_credentials(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Jira credentials found",
        )


@router.post("/jira/test", response_model=JiraConnectionTest)
async def test_jira_connection(
    test_credentials: JiraCredentialsCreate | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Test Jira connection with provided or stored credentials.

    If test_credentials is provided, tests with those credentials without saving.
    Otherwise, tests with stored credentials.
    """
    service = JiraCredentialsService(db)

    # Determine which credentials to use
    if test_credentials:
        # Use provided credentials for testing (without saving)
        test_url = test_credentials.base_url
        test_email = test_credentials.email
        test_token = test_credentials.api_token
        stored_credentials = None
    else:
        # Use stored credentials
        stored_credentials = service.get_credentials(current_user.id)
        if not stored_credentials:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No Jira credentials configured",
            )
        test_url = stored_credentials.base_url
        test_email = stored_credentials.email
        test_token = service.get_decrypted_token(stored_credentials)

    try:
        # Import here to avoid circular imports
        from src.config import JiraAuthConfig
        from src.jira_client import JiraClient

        # Create Jira client with credentials
        jira_config = JiraAuthConfig(
            method="pat",
            base_url=test_url,
            email=test_email,
            api_token=test_token,
        )
        client = JiraClient(jira_config)

        # Test connection by getting current user
        user_info = client.get_current_user()
        client.close()

        # Mark stored credentials as valid (only if testing stored credentials)
        if stored_credentials:
            service.mark_tested(stored_credentials, is_valid=True)

        return JiraConnectionTest(
            success=True,
            message="Connection successful",
            user_display_name=user_info.get("displayName"),
        )

    except Exception as e:
        # Mark stored credentials as invalid (only if testing stored credentials)
        if stored_credentials:
            service.mark_tested(stored_credentials, is_valid=False)

        return JiraConnectionTest(
            success=False,
            message=str(e),
        )


# ===================
# Telegram Linking
# ===================
@router.post("/telegram/link", response_model=TelegramLinkResponse)
async def request_telegram_link(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Request a verification code to link Telegram account."""
    service = TelegramLinkService(db)
    code, expires_at = service.create_verification_code(current_user.id)

    # Calculate seconds until expiration
    expires_in = int((expires_at - __import__("datetime").datetime.utcnow()).total_seconds())

    return TelegramLinkResponse(
        verification_code=code,
        expires_in=expires_in,
        bot_username="jira_feedback_bot",  # TODO: Get from config
        instructions=f"Send /link {code} to the bot to complete linking",
    )


@router.get("/telegram/status", response_model=TelegramStatusResponse)
async def get_telegram_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get Telegram link status."""
    service = TelegramLinkService(db)
    link = service.get_link(current_user.id)

    if not link or not link.is_verified:
        return TelegramStatusResponse(is_linked=False)

    return TelegramStatusResponse(
        is_linked=True,
        telegram_username=link.telegram_username,
        telegram_chat_id=link.telegram_chat_id,
        notifications_enabled=link.notifications_enabled,
        linked_at=link.created_at,
    )


@router.delete("/telegram/link", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_telegram(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Unlink Telegram account."""
    service = TelegramLinkService(db)
    if not service.unlink(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Telegram link found",
        )


@router.put("/telegram/settings", response_model=TelegramStatusResponse)
async def update_telegram_settings(
    settings_data: TelegramSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update Telegram notification settings."""
    service = TelegramLinkService(db)
    link = service.update_settings(current_user.id, settings_data.notifications_enabled)

    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No verified Telegram link found",
        )

    return TelegramStatusResponse(
        is_linked=True,
        telegram_username=link.telegram_username,
        telegram_chat_id=link.telegram_chat_id,
        notifications_enabled=link.notifications_enabled,
        linked_at=link.created_at,
    )
