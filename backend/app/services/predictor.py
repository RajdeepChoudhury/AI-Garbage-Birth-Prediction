"""Loads trained artifacts and turns raw ward rows into forecasts.

Derived outputs and how they are computed:
  predicted_volume      regression model output for tomorrow
  hotspot_probability   classifier probability of High plus Critical
  confidence            classifier probability of the predicted risk class
  urgency_score         0 to 100, half hotspot probability and half volume
                        relative to overflow capacity (a transparent heuristic)
  overflow date         linear projection from the predicted daily change
                        in volume; None when no overflow is expected within 7 days
"""
from __future__ import annotations

import json
import logging
import math
import sys
from datetime import date, timedelta
from functools import lru_cache

import joblib
import numpy as np
import pandas as pd

from app.config import get_settings

logger = logging.getLogger(__name__)

# API field name to dataset column name.
COLUMN_MAP = {
    "date": "Date", "ward": "Ward", "latitude": "Latitude", "longitude": "Longitude",
    "population": "Population", "traffic": "Traffic", "weather": "Weather",
    "rainfall": "Rainfall", "temperature": "Temperature", "humidity": "Humidity",
    "nearby_market_count": "Nearby Market Count", "nearby_school_count": "Nearby School Count",
    "restaurant_density": "Restaurant Density", "collection_frequency": "Collection Frequency",
    "complaint_count": "Complaint Count", "previous_garbage_volume": "Previous Garbage Volume",
    "festival_flag": "Festival Flag", "holiday_flag": "Holiday Flag", "construction_flag": "Construction Flag",
}
REQUIRED_COLUMNS = list(COLUMN_MAP.values())
RISK_ORDER = ["Low", "Medium", "High", "Critical"]


def cleaning_window(urgency: float) -> str:
    if urgency >= 75:
        return "Within 6 hours, before the next morning shift"
    if urgency >= 50:
        return "Within 24 hours"
    if urgency >= 25:
        return "Within 48 hours"
    return "Next scheduled collection"


class Predictor:
    def __init__(self) -> None:
        s = get_settings()
        self.capacity = s.overflow_capacity
        art = s.ml_dir / "artifacts"
        sys.path.insert(0, str(s.ml_dir))
        from features import prepare_features  # noqa: PLC0415 (path set just above)

        self._prepare = prepare_features
        self.regressor = joblib.load(art / "best_regressor.joblib")
        self.classifier = joblib.load(art / "best_classifier.joblib")
        self.columns: list[str] = json.loads((art / "feature_columns.json").read_text())
        self._explainer = None
        logger.info("Predictor loaded from %s", art)

    def predict(self, raw: pd.DataFrame) -> list[dict]:
        """raw uses dataset column names. Returns one dict per row."""
        X = self._prepare(raw)[self.columns]
        volume = np.clip(np.asarray(self.regressor.predict(X), dtype=float), 0, None)
        proba = np.asarray(self.classifier.predict_proba(X), dtype=float)
        classes = [int(c) for c in np.asarray(self.classifier.classes_).ravel()]

        factors = self._factors(X)
        results: list[dict] = []
        for i, (_, row) in enumerate(raw.iterrows()):
            p = dict(zip(classes, proba[i]))
            hotspot = float(p.get(2, 0.0) + p.get(3, 0.0))
            top = max(p, key=p.get)
            urgency = 100.0 * (0.5 * hotspot + 0.5 * min(volume[i] / (1.5 * self.capacity), 1.0))
            forecast_date = pd.Timestamp(row["Date"]).date() + timedelta(days=1)
            results.append(
                {
                    "ward": int(row["Ward"]),
                    "latitude": float(row["Latitude"]),
                    "longitude": float(row["Longitude"]),
                    "forecast_date": forecast_date,
                    "predicted_volume": round(float(volume[i]), 3),
                    "risk_level": RISK_ORDER[top],
                    "hotspot_probability": round(hotspot, 4),
                    "urgency_score": round(urgency, 1),
                    "confidence": round(float(p[top]), 4),
                    "recommended_cleaning_time": cleaning_window(urgency),
                    "predicted_overflow_date": self._overflow(
                        forecast_date, float(volume[i]), float(row["Previous Garbage Volume"])
                    ),
                    "top_factors": factors[i],
                }
            )
        return results

    def _factors(self, X: pd.DataFrame, top_k: int = 5) -> list[list[dict]]:
        """SHAP contributions of the regressor. Explanations are supplementary,
        so a failure is logged and the forecast is still returned."""
        try:
            if self._explainer is None:
                import shap  # noqa: PLC0415 (heavy import, only needed here)

                self._explainer = shap.TreeExplainer(self.regressor)
            values = np.asarray(self._explainer.shap_values(X))
            out: list[list[dict]] = []
            for i in range(len(X)):
                order = np.argsort(-np.abs(values[i]))[:top_k]
                out.append(
                    [
                        {
                            "feature": self.columns[j],
                            "value": round(float(X.iloc[i, j]), 3),
                            "impact": round(float(values[i, j]), 3),
                        }
                        for j in order
                    ]
                )
            return out
        except Exception:
            logger.exception("SHAP explanation failed")
            return [[] for _ in range(len(X))]

    def _overflow(self, forecast_date: date, volume: float, previous: float) -> date | None:
        if volume >= self.capacity:
            return forecast_date
        growth = volume - previous
        if growth <= 0:
            return None
        days = math.ceil((self.capacity - volume) / growth)
        return forecast_date + timedelta(days=days) if days <= 7 else None


@lru_cache
def get_predictor() -> Predictor:
    return Predictor()
