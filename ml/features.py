"""Feature engineering shared by training and the prediction service.

Kept free of heavy imports so the API can load it quickly.
"""
from __future__ import annotations

import pandas as pd

RISK_ORDER = ["Low", "Medium", "High", "Critical"]
REG_TARGET = "Garbage Volume Tomorrow"
CLS_TARGET = "Risk Level"
NON_FEATURES = ["Date", "Ward", REG_TARGET, CLS_TARGET, "Hotspot Probability"]
WEATHER_ORDER = ["Clear", "Cloudy", "Rain", "Heavy Rain"]


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    """Turn raw rows into model features. Shared with the prediction service."""
    out = df.copy()
    out["Date"] = pd.to_datetime(out["Date"])
    out["DayOfWeek"] = out["Date"].dt.dayofweek
    out["Month"] = out["Date"].dt.month
    out["IsWeekend"] = (out["DayOfWeek"] >= 5).astype(int)
    out["Weather"] = out["Weather"].map({w: i for i, w in enumerate(WEATHER_ORDER)}).fillna(0).astype(int)
    out["Market Pressure"] = out["Nearby Market Count"] * out["Traffic"] / 100.0
    out["Pickup Gap"] = 7.0 / out["Collection Frequency"].clip(lower=1)
    return out.drop(columns=[c for c in NON_FEATURES if c in out.columns])
