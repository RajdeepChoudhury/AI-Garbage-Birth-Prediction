"""Builds grounded prompts from stored forecasts and asks Groq.

The model only sees numbers computed by our pipeline, passed in the prompt.
Anything it says about the city should come from that context.
"""
import re
from collections import Counter

from app.config import get_settings
from app.models import Prediction
from app.services import groq_client

SYSTEM_PROMPT = (
    "You are a municipal waste management assistant for city officers. "
    "Use only the forecast data provided in the context. Never invent numbers, wards, trucks, "
    "or dates that are not in the context. If the context lacks something needed to answer, say so "
    "and say what data would be needed. Volumes are in model volume units, not tonnes, unless told otherwise. "
    "Forecasts are statistical estimates, so mention uncertainty using the confidence values when relevant. "
    "Write in clear, plain language that a non technical officer can act on. Be concise."
)

TASKS = {
    "ask": "Answer the officer's question using the context.",
    "daily_plan": (
        "Create tomorrow's cleaning plan. Order wards by urgency and group them by their recommended cleaning "
        "window into time slots. For each ward give one line: ward, risk, why it is prioritised, and the action. "
        "If the fleet size is not provided, do not invent truck counts: give priority tiers and ask for the fleet size."
    ),
    "executive_report": (
        "Write a short executive report in markdown with these headings: Headline, Risk Summary, Priority Wards "
        "(top five), Main Drivers, Recommended Actions, Limitations. Keep it under 350 words."
    ),
    "explain_ward": (
        "Explain in simple language, in under 120 words, why this ward received its forecast. Use the listed "
        "factors: say which ones push the forecast up and which push it down, and end with one practical suggestion."
    ),
}


class NoForecasts(Exception):
    """Nothing has been predicted yet."""


def _line(p: Prediction) -> str:
    overflow = p.predicted_overflow_date.isoformat() if p.predicted_overflow_date else "none within 7 days"
    return (
        f"Ward {p.ward}: risk {p.risk_level}, volume {p.predicted_volume:.2f}, hotspot probability "
        f"{p.hotspot_probability:.2f}, urgency {p.urgency_score:.0f}, confidence {p.confidence:.2f}, "
        f"cleaning {p.recommended_cleaning_time}, overflow {overflow}"
    )


def build_context(
    forecasts: list[Prediction],
    focus_ward: int | None = None,
    available_trucks: int | None = None,
    top_n: int = 15,
) -> str:
    if not forecasts:
        raise NoForecasts("No forecasts available. Upload data or run a prediction first.")
    s = get_settings()
    ranked = sorted(forecasts, key=lambda p: p.urgency_score, reverse=True)
    counts = Counter(p.risk_level for p in forecasts)
    parts = [
        f"Forecast date: {max(p.forecast_date for p in forecasts).isoformat()}",
        f"Wards forecast: {len(forecasts)}. Risk counts: "
        + ", ".join(f"{k} {counts.get(k, 0)}" for k in ("Low", "Medium", "High", "Critical")),
        f"Overflow threshold: {s.overflow_capacity} volume units per ward.",
        f"Trucks available: {available_trucks}" if available_trucks is not None else "Trucks available: not provided",
        f"Top {min(top_n, len(ranked))} wards by urgency:",
        *[_line(p) for p in ranked[:top_n]],
    ]
    if focus_ward is not None:
        match = next((p for p in forecasts if p.ward == focus_ward), None)
        if match is None:
            parts.append(f"Ward {focus_ward} has no forecast in the data.")
        else:
            parts.append(f"Focus ward details. {_line(match)}")
            if match.top_factors:
                parts.append("Factors for this ward (impact in volume units, positive raises the forecast):")
                parts += [f"{f['feature']} = {f['value']} (impact {f['impact']:+.2f})" for f in match.top_factors]
    return "\n".join(parts)


def detect_ward(text: str) -> int | None:
    m = re.search(r"\bward\s*#?\s*(\d{1,4})\b", text, flags=re.IGNORECASE)
    return int(m.group(1)) if m else None


async def run(
    task: str,
    forecasts: list[Prediction],
    *,
    question: str | None = None,
    focus_ward: int | None = None,
    available_trucks: int | None = None,
    transport=None,
) -> dict:
    context = build_context(forecasts, focus_ward, available_trucks)
    user = f"Context:\n{context}\n\nTask: {TASKS[task]}"
    if question:
        user += f"\n\nOfficer's question: {question}"
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user}]
    answer = await groq_client.chat(messages, transport=transport)
    return {"answer": answer, "model": get_settings().groq_model, "wards_in_context": len(forecasts)}
