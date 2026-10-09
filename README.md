# AI Garbage Birth Prediction

A platform that forecasts where garbage is likely to pile up tomorrow, so a municipal team can schedule collection before it becomes a problem. It predicts volume, risk level, hotspot probability, urgency and an overflow date for each ward, shows them on a map, explains them with SHAP, and offers an AI assistant (Groq) that answers officer questions from the real forecasts.

**Important:** the bundled data is synthetic. Model scores reflect how well the models learn the synthetic rules, not how well they would forecast a real city. The code is structured so real municipal data can replace the generator.

## What is implemented

| Area | Status |
|---|---|
| Synthetic data generator, CSV upload with validation | Done |
| Random Forest, XGBoost, LightGBM, CatBoost comparison (MAE, RMSE, R2, precision, recall, F1) | Done |
| SHAP explanations stored with each forecast | Done |
| FastAPI backend, JWT with refresh rotation, four roles, audit log, rate limiting | Done |
| Groq assistant: ask, explain a ward, daily plan, executive report | Done (tested with a mocked Groq server only) |
| React dashboard: map, ranking, charts, model comparison, assistant, upload, dark mode | Done |
| Docker Compose, GitHub Actions CI | Written, not run in the build environment |
| LSTM, Temporal Fusion Transformer, Graph Neural Network | Not built |
| Heatmap layer, ward boundaries, cleaning routes, forecast timeline and trend charts | Not built |
| Email, SMS and push notifications, scheduler, automatic retraining | Not built |
| Alembic migrations, component level frontend tests, load testing | Not built |

## Quick start with Docker

1. Copy the environment file and set real secrets: `cp .env.example .env`
2. Train the models once (about a minute or two): `docker compose --profile train run --rm trainer`
3. Start everything: `docker compose up --build`
4. Open http://localhost:8080 and sign in with `ADMIN_EMAIL` and `ADMIN_PASSWORD` from your `.env`.
5. Go to Data upload and choose `ml/data/garbage_synthetic.csv`. The dashboard fills with forecasts for 40 wards.

The API documentation is served at http://localhost:8000/docs.

## Local development

```bash
# 1. Data and models
cd ml
pip install -r requirements.txt
python data/generate_synthetic.py --out data/garbage_synthetic.csv
python train.py

# 2. Backend (SQLite by default)
cd ../backend
pip install -r requirements-dev.txt
export SECRET_KEY=dev-secret ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD=adminpass123
uvicorn app.main:app --reload

# 3. Frontend
cd ../frontend
npm install
npm run dev
```

Run the tests with `python -m pytest` in `backend` (26 tests) and `npm test` in `frontend` (6 tests).

## Roles

| Role | Dashboard and models | Assistant | Predict | CSV upload | User admin and audit log |
|---|---|---|---|---|---|
| citizen | yes | no | no | no | no |
| analyst | yes | yes | yes | no | no |
| officer | yes | yes | yes | yes | no |
| admin | yes | yes | yes | yes | yes |

Public sign up creates citizens only. An admin creates staff accounts.

## Configuration

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | JWT signing key. The app refuses to start in production with the default. |
| `DATABASE_URL` | SQLAlchemy URL. SQLite by default, PostgreSQL in Docker. |
| `REDIS_URL` | Shared rate limit storage. In memory when empty. |
| `GROQ_API_KEY`, `GROQ_MODEL` | Assistant. Without a key the assistant returns a clear 503. Check the Groq documentation for current model names. |
| `OVERFLOW_CAPACITY` | Volume above which a ward counts as overflowing. Replace with real bin capacity. |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | Creates the first admin at startup. |
| `CORS_ORIGINS` | Allowed browser origins, as a JSON list. |

## More documentation

* [Architecture and diagrams](docs/ARCHITECTURE.md)
* [API reference](docs/API.md)
* [Models and how forecasts are computed](docs/MODELS.md)
* [Deployment and installation](docs/DEPLOYMENT.md)

## Known limitations

* Urgency score, cleaning window and overflow date are transparent heuristics built on model outputs. They are not separately trained models.
* Login tokens are kept in browser local storage. Move to secure cookies before a real deployment.
* Tables are created at startup. Add Alembic migrations before production, and only then run more than one backend worker.
* Forecasts for earlier dates are stored in the database, but no endpoint serves that history yet.
