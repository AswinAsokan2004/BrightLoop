import hashlib
import re
import secrets
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.config import settings
from app.core.exceptions import AuthenticationError
from app.models.enums import UserRole


def utcnow() -> datetime:
    return datetime.now(UTC)


def check_password_strength(password: str) -> str:
    """More than 8 characters, with an uppercase letter, a lowercase letter and a special character."""
    missing = []
    if len(password) <= 8:
        missing.append("more than 8 characters")
    if not re.search(r"[A-Z]", password):
        missing.append("an uppercase letter")
    if not re.search(r"[a-z]", password):
        missing.append("a lowercase letter")
    if not re.search(r"[^A-Za-z0-9\s]", password):
        missing.append("a special character")
    if missing:
        raise ValueError("Password must have " + ", ".join(missing))
    return password


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:  # malformed hash, e.g. placeholder seed data
        return False


def create_access_token(user_id: int, role: UserRole) -> str:
    now = utcnow()
    payload = {
        "sub": str(user_id),
        "role": role.value,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> int:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Invalid or expired access token") from exc
    if payload.get("type") != "access":
        raise AuthenticationError("Invalid access token")
    return int(payload["sub"])


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def new_opaque_token() -> tuple[str, str]:
    """Return (raw token for the client, hash to store). Only the hash is ever saved."""
    raw = secrets.token_urlsafe(32)
    return raw, hash_token(raw)
