"""
JWT and password security utilities.

- Access tokens carry: sub, iat, exp, jti, iss, aud, type
- Refresh tokens are stored as SHA-256 hashes; raw token returned to client only
- Never log token values
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.core.config import settings


def get_password_hash(password: str) -> str:
    """Hashes a plain text password using bcrypt."""
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain text password against a bcrypt hash."""
    try:
        pwd_bytes = plain_password.encode("utf-8")
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hashed_bytes)
    except Exception:
        return False


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validates password meets minimum strength requirements.

    Returns (is_valid, error_message).
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter."
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter."
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit."
    return True, ""


def create_access_token(subject: str | Any, expires_delta: timedelta | None = None) -> str:
    """
    Generates a signed JWT access token.

    Claims included:
      sub  — user ID (string)
      iat  — issued at
      exp  — expiration
      jti  — unique token ID (for future revocation)
      iss  — issuer
      aud  — audience
      type — "access"
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode: dict[str, Any] = {
        "sub": str(subject),
        "iat": datetime.now(timezone.utc),
        "exp": expire,
        "jti": str(uuid.uuid4()),
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "type": "access",
    }

    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> str | None:
    """
    Decodes a JWT access token.

    Validates: signature, expiry, issuer, audience, and token type.
    Returns the subject (user ID) on success, None on any failure.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
        )
        # Verify token type to prevent refresh tokens being used as access tokens
        if payload.get("type") != "access":
            return None
        return payload.get("sub")
    except jwt.PyJWTError:
        return None


def hash_refresh_token(raw_token: str) -> str:
    """
    Returns a SHA-256 hash of the raw refresh token for safe database storage.

    The raw token is returned to the client; only the hash is persisted.
    """
    return hashlib.sha256(raw_token.encode()).hexdigest()


def generate_refresh_token() -> tuple[str, str]:
    """
    Generates a new opaque refresh token.

    Returns (raw_token, hashed_token).
    raw_token  → send to client
    hashed_token → store in database
    """
    raw = secrets.token_urlsafe(64)
    hashed = hash_refresh_token(raw)
    return raw, hashed
