"""Prediction, CSV upload, forecast queries and model metrics."""
from __future__ import annotations

import io
import json
import logging

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import audit, get_current_user, require_roles
from app.models import Prediction, Role, User
from app.schemas import PredictionResult, PredictRequest, StoredPrediction, UploadSummary
from app.services.predictor import COLUMN_MAP, REQUIRED_COLUMNS, get_predictor

logger = logging.getLogger(__name__)
router = APIRouter(tags=["predictions"])
STAFF = (Role.admin, Role.officer, Role.analyst)
WEATHER = {"Clear", "Cloudy", "Rain", "Heavy Rain"}


def persist(db: Session, results: list[dict]) -> None:
    """Replace any stored forecast for the same ward and date."""
    for r in results:
        db.query(Prediction).filter(
            Prediction.ward == r["ward"], Prediction.forecast_date == r["forecast_date"]
        ).delete()
        db.add(Prediction(**r))
    db.commit()


@router.post("/predictions/predict", response_model=list[PredictionResult])
def predict(body: PredictRequest, db: Session = Depends(get_db), user: User = Depends(require_roles(*STAFF))):
    raw = pd.DataFrame([i.model_dump() for i in body.items]).rename(columns=COLUMN_MAP)
    results = get_predictor().predict(raw)
    persist(db, results)
    audit(db, user.id, "predict", f"{len(results)} rows")
    return results


def validate_csv(df: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Missing columns: {missing}")
    df = df[REQUIRED_COLUMNS].copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    numeric = [c for c in REQUIRED_COLUMNS if c not in ("Date", "Weather")]
    df[numeric] = df[numeric].apply(pd.to_numeric, errors="coerce")
    if df.isna().any().any():
        bad = df.columns[df.isna().any()].tolist()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Empty or invalid values in: {bad}")
    if not df["Weather"].isin(WEATHER).all():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Weather must be one of {sorted(WEATHER)}")
    for flag in ("Festival Flag", "Holiday Flag", "Construction Flag"):
        if not df[flag].isin([0, 1]).all():
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"{flag} must be 0 or 1")
    if (df["Collection Frequency"] < 1).any() or (df["Humidity"].between(0, 100) == False).any():  # noqa: E712
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Collection Frequency or Humidity out of range")
    return df


@router.post("/data/upload", response_model=UploadSummary)
async def upload_csv(
    file: UploadFile,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.admin, Role.officer)),
):
    """Upload daily ward data. Forecasts tomorrow for the latest date of each ward."""
    content = await file.read(get_settings().max_upload_bytes + 1)
    if len(content) > get_settings().max_upload_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File too large")
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Could not parse CSV")
    df = validate_csv(df)
    latest = df.sort_values("Date").groupby("Ward").tail(1)
    results = get_predictor().predict(latest)
    persist(db, results)
    counts = pd.Series([r["risk_level"] for r in results]).value_counts().to_dict()
    audit(db, user.id, "upload", f"{len(df)} rows, {file.filename}")
    return UploadSummary(rows_read=len(df), wards_forecast=len(results), risk_counts=counts)


@router.get("/predictions/latest", response_model=list[StoredPrediction])
def latest(
    risk_level: str | None = None,
    ward: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Most recent stored forecast for each ward, optionally filtered."""
    newest = select(Prediction.ward, func.max(Prediction.forecast_date).label("d")).group_by(Prediction.ward).subquery()
    q = select(Prediction).join(newest, (Prediction.ward == newest.c.ward) & (Prediction.forecast_date == newest.c.d))
    if risk_level:
        q = q.where(Prediction.risk_level == risk_level)
    if ward:
        q = q.where(Prediction.ward == ward)
    return db.scalars(q.order_by(Prediction.urgency_score.desc())).all()


@router.get("/models/metrics")
def model_metrics(user: User = Depends(get_current_user)):
    path = get_settings().ml_dir / "artifacts" / "metrics.json"
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Train the models first")
    return json.loads(path.read_text())
