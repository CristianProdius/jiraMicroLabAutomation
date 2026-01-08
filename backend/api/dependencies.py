"""FastAPI dependency injection utilities."""

from typing import Generator, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from api.config import get_settings
from api.db.database import SessionLocal
from api.auth.models import User
from api.auth.security import decode_token

settings = get_settings()

# OAuth2 scheme for JWT bearer tokens (optional, we also check cookies)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency.

    Yields a database session and ensures it's closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_token_from_request(
    request: Request,
    token_from_header: Optional[str] = Depends(oauth2_scheme),
) -> Optional[str]:
    """
    Extract token from Authorization header or cookies.
    Prefers Authorization header, falls back to cookie.
    """
    # First check Authorization header
    if token_from_header:
        return token_from_header

    # Fall back to cookie
    return request.cookies.get("access_token")


async def get_current_user(
    token: Optional[str] = Depends(get_token_from_request),
    db: Session = Depends(get_db),
) -> User:
    """
    Get the current authenticated user from JWT token.
    Token can be from Authorization header or HTTP-only cookie.

    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    payload = decode_token(token)
    if payload is None:
        raise credentials_exception

    # sub is stored as string in JWT, convert to int
    user_id_str = payload.get("sub")
    token_type: str = payload.get("type")

    if user_id_str is None or token_type != "access":
        raise credentials_exception

    try:
        user_id = int(user_id_str)
    except (TypeError, ValueError):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get the current active user.

    This is an alias for get_current_user that explicitly checks is_active.
    """
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get the current user if they are a superuser.

    Raises:
        HTTPException: If user is not a superuser
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return current_user


async def get_optional_user(
    token: Optional[str] = Depends(get_token_from_request),
    db: Session = Depends(get_db),
) -> User | None:
    """
    Get the current user if authenticated, otherwise return None.

    Useful for endpoints that work with or without authentication.
    """
    try:
        return await get_current_user(token, db)
    except HTTPException:
        return None
