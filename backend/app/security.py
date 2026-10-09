"""Password hashing and JWT helpers."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import HTTPException, status

from app.config import get_settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


def create_token(subject: int, kind: str, expires_in: timedelta) -> tuple[str, str, datetime]:
    """Return (token, jti, expiry). kind is 'access' or 'refresh'."""
    s = get_settings()
    jti = uuid.uuid4().hex
    exp = datetime.now(timezone.utc) + expires_in
    token = jwt.encode(
        {"sub": str(subject), "type": kind, "jti": jti, "exp": exp},
        s.secret_key,
        algorithm=s.jwt_algorithm,
    )
    return token, jti, exp


def decode_token(token: str, kind: str) -> dict:
    s = get_settings()
    try:
        payload = jwt.decode(token, s.secret_key, algorithms=[s.jwt_algorithm])
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    if payload.get("type") != kind:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong token type")
    return payload
