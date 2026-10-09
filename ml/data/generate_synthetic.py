"""Synthetic dataset generator for AI Garbage Birth Prediction.

Produces one row per ward per day with the columns required by the project
spec. The generating process is deliberately structured (not pure noise) so
that models can learn real signal: weekly seasonality, rain and festival
effects, market and restaurant proximity, and collection frequency all
influence tomorrow's garbage volume.

Swap this module for a real municipal data loader later; the output schema
is the contract the rest of the pipeline depends on.

Usage:
    python generate_synthetic.py --wards 40 --days 540 --out garbage_synthetic.csv
"""
from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger("synthetic")

# Approximate centre of Kolkata, used only to place demo wards on a map.
CITY_LAT, CITY_LON = 22.5726, 88.3639

WEATHER_TYPES = ["Clear", "Cloudy", "Rain", "Heavy Rain"]
RISK_LEVELS = ["Low", "Medium", "High", "Critical"]


@dataclass(frozen=True)
class WardProfile:
    ward: int
    latitude: float
    longitude: float
    population: int
    markets: int
    schools: int
    restaurant_density: float
    collection_frequency: int  # pickups per week
    base_traffic: float


def build_wards(n_wards: int, rng: np.random.Generator) -> list[WardProfile]:
    """Create static ward level attributes."""
    wards: list[WardProfile] = []
    for w in range(1, n_wards + 1):
        density_factor = rng.lognormal(mean=0.0, sigma=0.45)
        wards.append(
            WardProfile(
                ward=w,
                latitude=float(CITY_LAT + rng.normal(0, 0.06)),
                longitude=float(CITY_LON + rng.normal(0, 0.06)),
                population=int(np.clip(20000 * density_factor, 6000, 90000)),
                markets=int(rng.poisson(2.2 * density_factor)),
                schools=int(rng.poisson(3.0)),
                restaurant_density=float(np.round(rng.gamma(2.0, 3.0) * density_factor, 2)),
                collection_frequency=int(rng.choice([3, 4, 5, 6, 7], p=[0.1, 0.2, 0.3, 0.25, 0.15])),
                base_traffic=float(np.clip(rng.normal(55, 18) * density_factor**0.3, 10, 100)),
            )
        )
    return wards


def build_calendar(start: str, days: int, rng: np.random.Generator) -> pd.DataFrame:
    """City wide daily context: weather, festivals, holidays."""
    dates = pd.date_range(start=start, periods=days, freq="D")
    doy = dates.dayofyear.to_numpy()

    # Seasonal temperature (deg C) and humidity, monsoon peaking mid year.
    temperature = 27 + 6 * np.sin((doy - 100) / 365 * 2 * np.pi) + rng.normal(0, 1.5, days)
    monsoon = np.exp(-(((doy - 200) / 45.0) ** 2))
    rain_prob = 0.08 + 0.65 * monsoon
    rainy = rng.random(days) < rain_prob
    rainfall = np.where(rainy, rng.gamma(2.0, 9.0, days) * (0.6 + monsoon), 0.0)
    humidity = np.clip(55 + 30 * monsoon + 8 * rainy + rng.normal(0, 5, days), 25, 100)

    weather = np.select(
        [rainfall > 40, rainfall > 5, humidity > 75],
        ["Heavy Rain", "Rain", "Cloudy"],
        default="Clear",
    )

    # Festivals: a few multi day clusters per year.
    festival = np.zeros(days, dtype=int)
    n_clusters = max(3, days // 90)
    for start_idx in rng.choice(days - 5, size=n_clusters, replace=False):
        festival[start_idx : start_idx + int(rng.integers(2, 6))] = 1

    holiday = ((dates.dayofweek == 6) | (rng.random(days) < 0.02)).astype(int)

    return pd.DataFrame(
        {
            "Date": dates,
            "Weather": weather,
            "Rainfall": np.round(rainfall, 1),
            "Temperature": np.round(temperature, 1),
            "Humidity": np.round(humidity, 1),
            "Festival Flag": festival,
            "Holiday Flag": holiday,
        }
    )


def generate(n_wards: int, days: int, start: str, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    wards = build_wards(n_wards, rng)
    calendar = build_calendar(start, days, rng)

    # Slow moving construction activity per ward (runs of consecutive days).
    frames: list[pd.DataFrame] = []
    for wp in wards:
        cal = calendar.copy()
        n = len(cal)
        dow = cal["Date"].dt.dayofweek.to_numpy()

        construction = np.zeros(n, dtype=int)
        for s in rng.choice(n - 20, size=rng.integers(1, 4), replace=False):
            construction[s : s + int(rng.integers(7, 20))] = 1

        traffic = np.clip(
            wp.base_traffic + 10 * (dow < 5) - 8 * cal["Holiday Flag"].to_numpy() + rng.normal(0, 6, n),
            5,
            100,
        )

        # Pickups happen on a fixed subset of weekdays given frequency.
        pickup_days = set(np.linspace(0, 6, wp.collection_frequency, endpoint=False).astype(int))
        pickup_today = np.isin(dow, list(pickup_days))

        # Latent volume dynamics: backlog builds, a pickup clears most of it.
        volume = np.zeros(n)
        complaints = np.zeros(n, dtype=int)
        prev_volume = np.zeros(n)
        backlog = float(rng.uniform(1, 4))
        pop_scale = wp.population / 20000.0

        for t in range(n):
            daily_gen = (
                1.1 * pop_scale
                + 0.25 * wp.markets
                + 0.04 * wp.restaurant_density
                + 0.012 * traffic[t]
                + 0.6 * cal["Festival Flag"].iat[t]
                + 0.25 * cal["Holiday Flag"].iat[t]
                + 0.35 * construction[t]
                + 0.02 * max(cal["Rainfall"].iat[t] - 15, 0)  # wet waste, blocked drains
                + 0.03 * max(cal["Temperature"].iat[t] - 32, 0)
            )
            daily_gen *= float(rng.lognormal(0, 0.12))
            prev_volume[t] = backlog
            backlog += daily_gen
            if pickup_today[t]:
                backlog *= float(rng.uniform(0.08, 0.22))
            volume[t] = backlog
            complaints[t] = rng.poisson(max(backlog - 4.0, 0) * 0.5)

        df = pd.DataFrame(
            {
                "Date": cal["Date"],
                "Ward": wp.ward,
                "Latitude": np.round(wp.latitude, 5),
                "Longitude": np.round(wp.longitude, 5),
                "Population": wp.population,
                "Traffic": np.round(traffic, 1),
                "Weather": cal["Weather"],
                "Rainfall": cal["Rainfall"],
                "Temperature": cal["Temperature"],
                "Humidity": cal["Humidity"],
                "Nearby Market Count": wp.markets,
                "Nearby School Count": wp.schools,
                "Restaurant Density": wp.restaurant_density,
                "Collection Frequency": wp.collection_frequency,
                "Complaint Count": complaints,
                "Previous Garbage Volume": np.round(prev_volume, 2),
                "Festival Flag": cal["Festival Flag"],
                "Holiday Flag": cal["Holiday Flag"],
                "Construction Flag": construction,
            }
        )
        # Target is tomorrow's volume, so shift within the ward.
        df["Garbage Volume Tomorrow"] = np.round(pd.Series(volume).shift(-1).to_numpy(), 2)
        frames.append(df)

    data = pd.concat(frames, ignore_index=True).dropna(subset=["Garbage Volume Tomorrow"])

    # Risk labels from within dataset quantiles so every class is represented.
    q = data["Garbage Volume Tomorrow"].quantile([0.5, 0.8, 0.95]).to_numpy()
    data["Risk Level"] = pd.cut(
        data["Garbage Volume Tomorrow"],
        bins=[-np.inf, q[0], q[1], q[2], np.inf],
        labels=RISK_LEVELS,
    ).astype(str)

    # Hotspot probability: smooth function of volume relative to a capacity threshold.
    capacity = q[1]
    z = (data["Garbage Volume Tomorrow"] - capacity) / (0.35 * capacity)
    data["Hotspot Probability"] = np.round(1 / (1 + np.exp(-z)), 4)

    return data.sort_values(["Date", "Ward"]).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--wards", type=int, default=40)
    parser.add_argument("--days", type=int, default=540)
    parser.add_argument("--start", type=str, default="2025-01-01")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=Path("garbage_synthetic.csv"))
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    data = generate(args.wards, args.days, args.start, args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(args.out, index=False)
    logger.info("Wrote %d rows x %d columns to %s", *data.shape, args.out)
    logger.info("Risk distribution:\n%s", data["Risk Level"].value_counts(normalize=True).round(3))


if __name__ == "__main__":
    main()
