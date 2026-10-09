"""Registration, login, refresh token rotation, current user."""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import audit, get_current_user
from app.models import RefreshToken, Role, User, utcnow
from app.schemas import LoginRequest, RefreshRequest, TokenPair, UserCreate, UserOut
from app.security import create_token, decode_token, hash_password, verify_password

_s = get_settings()
router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address, storage_uri=_s.redis_url or "memory://")


def issue_pair(db: Session, user: User) -> TokenPair:
    access, _, _ = create_token(user.id, "access", timedelta(minutes=_s.access_token_minutes))
    refresh, jti, exp = create_token(user.id, "refresh", timedelta(days=_s.refresh_token_days))
    db.add(RefreshToken(jti=jti, user_id=user.id, expires_at=exp))
    db.commit()
    return TokenPair(access_token=access, refresh_token=refresh)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit(_s.rate_limit_login)
def register(request: Request, body: UserCreate, db: Session = Depends(get_db)) -> User:
    """Public sign up always creates a citizen. Staff roles are assigned by an admin."""
    if db.scalar(select(User).where(User.email == body.email.lower())):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = User(email=body.email.lower(), hashed_password=hash_password(body.password), role=Role.citizen)
    db.add(user)
    db.commit()
    audit(db, user.id, "register")
    return user


@router.post("/login", response_model=TokenPair)
@limiter.limit(_s.rate_limit_login)
def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)) -> TokenPair:
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not user.is_active or not verify_password(body.password, user.hashed_password):
        audit(db, None, "login_failed", body.email)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    audit(db, user.id, "login")
    return issue_pair(db, user)


@router.post("/refresh", response_model=TokenPair)
@limiter.limit(_s.rate_limit_login)
def refresh(request: Request, body: RefreshRequest, db: Session = Depends(get_db)) -> TokenPair:
    payload = decode_token(body.refresh_token, "refresh")
    record = db.get(RefreshToken, payload["jti"])
    if record is None or record.revoked:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token revoked")
    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or inactive")
    record.revoked = True  # rotation: each refresh token works once
    db.commit()
    return issue_pair(db, user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user
