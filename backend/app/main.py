"""FastAPI application entry point."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import select

from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.models import Role, User
from app.routers import admin, assistant, auth, predictions
from app.routers.auth import limiter
from app.security import hash_password

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("app")


def seed_admin() -> None:
    """Create a first admin from ADMIN_EMAIL and ADMIN_PASSWORD when set."""
    import os

    email, password = os.getenv("ADMIN_EMAIL"), os.getenv("ADMIN_PASSWORD")
    if not email or not password:
        return
    with SessionLocal() as db:
        if not db.scalar(select(User).where(User.email == email.lower())):
            db.add(User(email=email.lower(), hashed_password=hash_password(password), role=Role.admin))
            db.commit()
            logger.info("Seeded admin user %s", email)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)  # swap for Alembic migrations before production
    seed_admin()
    yield


app = FastAPI(title="AI Garbage Birth Prediction API", version="0.4.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router)
app.include_router(predictions.router)
app.include_router(admin.router)
app.include_router(assistant.router)


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health", tags=["system"])
def health() -> dict:
    from app.services.predictor import get_predictor

    try:
        get_predictor()
        model_loaded = True
    except Exception:
        logger.exception("Model artifacts not loadable")
        model_loaded = False
    return {"status": "ok", "model_loaded": model_loaded}
