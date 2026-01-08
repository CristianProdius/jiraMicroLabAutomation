"""Security utilities for authentication."""

from datetime import datetime, timedelta
from typing import Optional
import secrets

from jose import JWTError, jwt
import bcrypt
from cryptography.fernet import Fernet

from api.config import get_settings

settings = get_settings()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


def get_password_hash(password: str) -> str:
    """Hash a password."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None


def generate_verification_code() -> str:
    """Generate a random verification code for Telegram linking."""
    return secrets.token_hex(4).upper()  # 8 character hex code


class CredentialEncryptor:
    """Encrypt and decrypt sensitive credentials like Jira API tokens."""

    def __init__(self):
        key = settings.encryption_key
        if key:
            self.fernet = Fernet(key.encode() if isinstance(key, str) else key)
        else:
            # Generate a key if not provided (not recommended for production)
            self.fernet = Fernet(Fernet.generate_key())

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string."""
        return self.fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a string."""
        return self.fernet.decrypt(ciphertext.encode()).decode()


# Singleton encryptor instance
_encryptor: Optional[CredentialEncryptor] = None


def get_encryptor() -> CredentialEncryptor:
    """Get the credential encryptor instance."""
    global _encryptor
    if _encryptor is None:
        _encryptor = CredentialEncryptor()
    return _encryptor
