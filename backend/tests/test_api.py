from pathlib import Path

from tests.conftest import login

SAMPLE = {
    "date": "2026-10-01", "ward": 17, "latitude": 22.57, "longitude": 88.36, "population": 42000,
    "traffic": 70, "weather": "Heavy Rain", "rainfall": 55, "temperature": 31, "humidity": 90,
    "nearby_market_count": 4, "nearby_school_count": 3, "restaurant_density": 12, "collection_frequency": 3,
    "complaint_count": 6, "previous_garbage_volume": 4.5, "festival_flag": 1, "holiday_flag": 0,
    "construction_flag": 0,
}
CSV = Path(__file__).resolve().parents[2] / "ml" / "data" / "garbage_synthetic.csv"


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["model_loaded"] is True


def test_register_creates_citizen_and_rejects_duplicates(client):
    body = {"email": "new@citytest.com", "password": "longenough1"}
    r = client.post("/auth/register", json=body)
    assert r.status_code == 201 and r.json()["role"] == "citizen"
    assert client.post("/auth/register", json=body).status_code == 409


def test_weak_password_rejected(client):
    r = client.post("/auth/register", json={"email": "weak@citytest.com", "password": "short"})
    assert r.status_code == 422


def test_login_wrong_password(client):
    r = client.post("/auth/login", json={"email": "admin@citytest.com", "password": "wrongpass"})
    assert r.status_code == 401


def test_protected_route_needs_token(client):
    assert client.get("/predictions/latest").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_refresh_rotation(client):
    pair = login(client, "admin@citytest.com", "adminpass123")
    ok = client.post("/auth/refresh", json={"refresh_token": pair["refresh_token"]})
    assert ok.status_code == 200
    reuse = client.post("/auth/refresh", json={"refresh_token": pair["refresh_token"]})
    assert reuse.status_code == 401
    # An access token must not work as a refresh token.
    assert client.post("/auth/refresh", json={"refresh_token": pair["access_token"]}).status_code == 401


def test_citizen_cannot_predict_or_admin(client, citizen_headers):
    assert client.post("/predictions/predict", json={"items": [SAMPLE]}, headers=citizen_headers).status_code == 403
    assert client.get("/admin/audit-logs", headers=citizen_headers).status_code == 403


def test_predict_returns_full_forecast(client, officer_headers):
    r = client.post("/predictions/predict", json={"items": [SAMPLE]}, headers=officer_headers)
    assert r.status_code == 200, r.text
    out = r.json()[0]
    assert out["forecast_date"] == "2026-10-02"
    assert out["risk_level"] in {"Low", "Medium", "High", "Critical"}
    assert 0 <= out["hotspot_probability"] <= 1 and 0 <= out["urgency_score"] <= 100
    assert out["predicted_volume"] >= 0 and out["recommended_cleaning_time"]


def test_predict_validates_input(client, officer_headers):
    bad = {**SAMPLE, "humidity": 140, "weather": "Snow"}
    r = client.post("/predictions/predict", json={"items": [bad]}, headers=officer_headers)
    assert r.status_code == 422


def test_high_load_ward_scores_riskier_than_quiet_ward(client, officer_headers):
    quiet = {**SAMPLE, "ward": 2, "previous_garbage_volume": 0.3, "population": 9000, "nearby_market_count": 0,
             "festival_flag": 0, "weather": "Clear", "rainfall": 0, "collection_frequency": 7, "complaint_count": 0}
    r = client.post("/predictions/predict", json={"items": [SAMPLE, quiet]}, headers=officer_headers).json()
    assert r[0]["predicted_volume"] > r[1]["predicted_volume"]
    assert r[0]["urgency_score"] > r[1]["urgency_score"]


def test_csv_upload_and_latest(client, officer_headers):
    lines = CSV.read_text().splitlines()
    sample = "\n".join(lines[:1] + lines[-400:])  # header plus recent rows
    r = client.post("/data/upload", files={"file": ("data.csv", sample, "text/csv")}, headers=officer_headers)
    assert r.status_code == 200, r.text
    assert r.json()["wards_forecast"] > 0
    latest = client.get("/predictions/latest", headers=officer_headers).json()
    assert len(latest) >= r.json()["wards_forecast"]
    urgencies = [p["urgency_score"] for p in latest]
    assert urgencies == sorted(urgencies, reverse=True)


def test_csv_upload_rejects_bad_files(client, officer_headers):
    r = client.post("/data/upload", files={"file": ("x.csv", "a,b\n1,2\n", "text/csv")}, headers=officer_headers)
    assert r.status_code == 422 and "Missing columns" in r.text


def test_metrics_endpoint(client, citizen_headers):
    r = client.get("/models/metrics", headers=citizen_headers)
    assert r.status_code == 200 and "regression" in r.json()


def test_audit_log_records_actions(client, admin_headers):
    logs = client.get("/admin/audit-logs", headers=admin_headers).json()
    actions = {entry["action"] for entry in logs}
    assert {"login", "predict", "upload"} <= actions
