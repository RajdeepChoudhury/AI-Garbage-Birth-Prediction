"""Request and response models with input validation."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import Role

Flag = Literal[0, 1]


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class AdminUserCreate(UserCreate):
    role: Role


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    role: Role
    is_active: bool


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(max_length=72)


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class WardDayInput(BaseModel):
    """One ward on one day. The forecast is for the following day."""

    date: date
    ward: int = Field(ge=1)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    population: int = Field(ge=0, le=5_000_000)
    traffic: float = Field(ge=0, le=100)
    weather: Literal["Clear", "Cloudy", "Rain", "Heavy Rain"]
    rainfall: float = Field(ge=0, le=1000)
    temperature: float = Field(ge=-20, le=60)
    humidity: float = Field(ge=0, le=100)
    nearby_market_count: int = Field(ge=0, le=500)
    nearby_school_count: int = Field(ge=0, le=500)
    restaurant_density: float = Field(ge=0, le=1000)
    collection_frequency: int = Field(ge=1, le=14)
    complaint_count: int = Field(ge=0, le=100_000)
    previous_garbage_volume: float = Field(ge=0, le=1000)
    festival_flag: Flag
    holiday_flag: Flag
    construction_flag: Flag


class PredictRequest(BaseModel):
    items: list[WardDayInput] = Field(min_length=1, max_length=500)


class Factor(BaseModel):
    """One feature's SHAP contribution to the volume forecast."""

    feature: str
    value: float
    impact: float  # positive raises the forecast, in volume units


class PredictionResult(BaseModel):
    ward: int
    latitude: float
    longitude: float
    forecast_date: date
    predicted_volume: float
    risk_level: str
    hotspot_probability: float
    urgency_score: float
    confidence: float
    recommended_cleaning_time: str
    predicted_overflow_date: date | None
    top_factors: list[Factor] | None = None


class StoredPrediction(PredictionResult):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


class UploadSummary(BaseModel):
    rows_read: int
    wards_forecast: int
    risk_counts: dict[str, int]


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int | None
    action: str
    detail: str
    created_at: datetime
