"""AI assistant endpoints backed by Groq. Staff roles only."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import audit, require_roles
from app.models import Prediction, Role, User
from app.routers.auth import limiter
from app.services import assistant
from app.services.groq_client import AssistantNotConfigured, AssistantUpstreamError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/assistant", tags=["assistant"])
STAFF = (Role.admin, Role.officer, Role.analyst)
_limit = get_settings().rate_limit_assistant


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    ward: int | None = Field(default=None, ge=1)
    available_trucks: int | None = Field(default=None, ge=0, le=10_000)


class PlanRequest(BaseModel):
    available_trucks: int | None = Field(default=None, ge=0, le=10_000)


class AssistantReply(BaseModel):
    answer: str
    model: str
    wards_in_context: int


def latest_forecasts(db: Session) -> list[Prediction]:
    newest = select(Prediction.ward, func.max(Prediction.forecast_date).label("d")).group_by(Prediction.ward).subquery()
    q = select(Prediction).join(newest, (Prediction.ward == newest.c.ward) & (Prediction.forecast_date == newest.c.d))
    return list(db.scalars(q).all())


async def _respond(db: Session, user: User, task: str, **kwargs) -> AssistantReply:
    try:
        result = await assistant.run(task, latest_forecasts(db), **kwargs)
    except assistant.NoForecasts as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc))
    except AssistantNotConfigured:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Assistant is not configured. Set GROQ_API_KEY.")
    except AssistantUpstreamError:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "The AI service is unavailable. Please try again shortly.")
    audit(db, user.id, f"assistant_{task}")
    return AssistantReply(**result)


@router.post("/ask", response_model=AssistantReply)
@limiter.limit(_limit)
async def ask(request: Request, body: AskRequest, db: Session = Depends(get_db), user: User = Depends(require_roles(*STAFF))):
    ward = body.ward or assistant.detect_ward(body.question)
    return await _respond(db, user, "ask", question=body.question, focus_ward=ward, available_trucks=body.available_trucks)


@router.get("/explain/{ward}", response_model=AssistantReply)
@limiter.limit(_limit)
async def explain_ward(request: Request, ward: int, db: Session = Depends(get_db), user: User = Depends(require_roles(*STAFF))):
    return await _respond(db, user, "explain_ward", focus_ward=ward)


@router.post("/daily-plan", response_model=AssistantReply)
@limiter.limit(_limit)
async def daily_plan(request: Request, body: PlanRequest, db: Session = Depends(get_db), user: User = Depends(require_roles(*STAFF))):
    return await _respond(db, user, "daily_plan", available_trucks=body.available_trucks)


@router.post("/executive-report", response_model=AssistantReply)
@limiter.limit(_limit)
async def executive_report(request: Request, body: PlanRequest, db: Session = Depends(get_db), user: User = Depends(require_roles(*STAFF))):
    return await _respond(db, user, "executive_report", available_trucks=body.available_trucks)
