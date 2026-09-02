"""Password hashing (bcrypt) and JWT access/refresh tokens.

Kept dependency-light and side-effect-free so it is unit-testable without a DB.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import get_settings

settings = get_settings()

TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"

# bcrypt only considers the first 72 bytes of the password.
_BCRYPT_MAX_BYTES = 72


def _truncate(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_truncate(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_truncate(password), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def _create_token(subject: str | uuid.UUID, token_type: str, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(subject),
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str | uuid.UUID) -> str:
    return _create_token(
        subject, TOKEN_TYPE_ACCESS, timedelta(minutes=settings.access_token_expire_minutes)
    )


def create_refresh_token(subject: str | uuid.UUID) -> str:
    return _create_token(
        subject, TOKEN_TYPE_REFRESH, timedelta(days=settings.refresh_token_expire_days)
    )


def decode_token(token: str) -> dict:
    """Decode and verify a token. Raises ``jwt.PyJWTError`` on invalid/expired."""
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
