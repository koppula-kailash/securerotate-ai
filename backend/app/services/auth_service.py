"""
SecureRotate AI - Authentication Service
Handles secure password hashing (Argon2 via pwdlib with PBKDF2/bcrypt fallback) and JWT access token creation/verification.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import hashlib
import os
import secrets
import jwt

from app.core.config import settings

# Attempt Argon2 via pwdlib, otherwise fallback to hashlib PBKDF2-HMAC-SHA256
_use_pwdlib = False
try:
    from pwdlib import PasswordHash
    _password_hasher = PasswordHash.recommended()
    _use_pwdlib = True
except (ImportError, ModuleNotFoundError):
    _password_hasher = None


def hash_password(password: str) -> str:
    """Hashes password using Argon2 via pwdlib or salted PBKDF2-HMAC-SHA256."""
    if _use_pwdlib and _password_hasher is not None:
        try:
            return _password_hasher.hash(password)
        except Exception:
            pass

    # High-security standard library fallback: PBKDF2 with 200,000 iterations
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 200000)
    return f"pbkdf2_sha256$200000${salt}${key.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies plain password against stored Argon2 or PBKDF2 hash."""
    if not hashed_password or not plain_password:
        return False

    if _use_pwdlib and _password_hasher is not None:
        try:
            if _password_hasher.verify(plain_password, hashed_password):
                return True
        except Exception:
            pass

    # Check PBKDF2 format
    if hashed_password.startswith("pbkdf2_sha256$"):
        try:
            parts = hashed_password.split("$")
            if len(parts) == 4:
                iterations = int(parts[1])
                salt = parts[2]
                expected_hex = parts[3]
                key = hashlib.pbkdf2_hmac('sha256', plain_password.encode('utf-8'), salt.encode('utf-8'), iterations)
                return secrets.compare_digest(key.hex(), expected_hex)
        except Exception:
            return False

    return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Creates a signed JWT access token containing claims: user_id, username, role, exp.
    Uses JWT_SECRET_KEY and JWT_ALGORITHM from application configuration.
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire_minutes = getattr(settings, "JWT_ACCESS_TOKEN_EXPIRE_MINUTES", getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 120))
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=expire_minutes)

    to_encode.update({
        "exp": expire,
        "iat": now,
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decodes and verifies a signed JWT access token.
    Returns payload dictionary if valid, or None if expired/invalid.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except (jwt.PyJWTError, Exception):
        return None
