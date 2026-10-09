"""Admin only user management and audit log access."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import audit, require_roles
from app.models import AuditLog, Role, User
from app.schemas import AdminUserCreate, AuditLogOut, UserOut
from app.security import hash_password

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(body: AdminUserCreate, db: Session = Depends(get_db), admin: User = Depends(require_roles(Role.admin))):
    if db.scalar(select(User).where(User.email == body.email.lower())):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = User(email=body.email.lower(), hashed_password=hash_password(body.password), role=body.role)
    db.add(user)
    db.commit()
    audit(db, admin.id, "create_user", f"{user.email} as {user.role.value}")
    return user


@router.get("/audit-logs", response_model=list[AuditLogOut])
def audit_logs(limit: int = 100, db: Session = Depends(get_db), admin: User = Depends(require_roles(Role.admin))):
    return db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(min(limit, 500))).all()
