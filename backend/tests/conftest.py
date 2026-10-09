import os
import tempfile

# Settings must be in place before the app modules are imported.
_db = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db}"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["ADMIN_EMAIL"] = "admin@citytest.com"
os.environ["ADMIN_PASSWORD"] = "adminpass123"
os.environ["RATE_LIMIT_LOGIN"] = "1000/minute"

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def login(client, email, password):
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(scope="session")
def admin_headers(client):
    return {"Authorization": f"Bearer {login(client, 'admin@citytest.com', 'adminpass123')['access_token']}"}


@pytest.fixture(scope="session")
def officer_headers(client, admin_headers):
    r = client.post("/admin/users", json={"email": "officer@citytest.com", "password": "officerpass1", "role": "officer"},
                    headers=admin_headers)
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {login(client, 'officer@citytest.com', 'officerpass1')['access_token']}"}


@pytest.fixture(scope="session")
def citizen_headers(client):
    client.post("/auth/register", json={"email": "citizen@citytest.com", "password": "citizenpass1"})
    return {"Authorization": f"Bearer {login(client, 'citizen@citytest.com', 'citizenpass1')['access_token']}"}
