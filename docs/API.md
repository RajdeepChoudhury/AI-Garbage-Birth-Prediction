# API reference

Interactive documentation is served by the backend at `/docs`. Protected routes expect `Authorization: Bearer <access token>`.

## Authentication

| Method and path | Access | Purpose |
|---|---|---|
| POST /auth/register | public, rate limited | Create a citizen account. Password 8 to 72 characters. |
| POST /auth/login | public, rate limited | Returns access and refresh tokens. |
| POST /auth/refresh | public, rate limited | Exchange a refresh token for a new pair. Each refresh token works once. |
| GET /auth/me | any signed in user | Current user. |

## Forecasts

| Method and path | Access | Purpose |
|---|---|---|
| POST /predictions/predict | admin, officer, analyst | Forecast up to 500 ward days. Inputs are range checked. |
| POST /data/upload | admin, officer | Upload a CSV up to 10 MB. Forecasts tomorrow for the latest row of each ward. |
| GET /predictions/latest | any signed in user | Latest forecast per ward, sorted by urgency. Filters: `risk_level`, `ward`. |
| GET /models/metrics | any signed in user | Model comparison and feature importance. |

A forecast contains: ward, latitude, longitude, forecast_date, predicted_volume, risk_level, hotspot_probability, urgency_score, confidence, recommended_cleaning_time, predicted_overflow_date and top_factors. See [Models](MODELS.md) for how each field is computed.

## Assistant

All assistant routes need admin, officer or analyst, and are limited to 20 requests per minute.

| Method and path | Purpose |
|---|---|
| POST /assistant/ask | Body: `question` (3 to 1000 characters), optional `ward`, optional `available_trucks`. A ward mentioned in the question is detected automatically. |
| GET /assistant/explain/{ward} | Plain language explanation of one ward. |
| POST /assistant/daily-plan | Tomorrow's cleaning plan. Optional `available_trucks`. |
| POST /assistant/executive-report | Short markdown report. Optional `available_trucks`. |

Errors: 409 when no forecasts exist yet, 503 when `GROQ_API_KEY` is not set, 502 when Groq fails.

## Administration

| Method and path | Access | Purpose |
|---|---|---|
| POST /admin/users | admin | Create a user with any role. |
| GET /admin/audit-logs | admin | Recent audit entries. |
| GET /health | public | Service status and whether the models loaded. |

## Common status codes

401 missing or invalid token. 403 role not allowed. 413 upload too large. 422 invalid input or CSV. 429 rate limit reached.
