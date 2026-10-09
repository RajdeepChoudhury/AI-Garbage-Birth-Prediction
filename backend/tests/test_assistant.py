import asyncio
from datetime import date

import httpx
import pytest

from app.config import get_settings
from app.models import Prediction
from app.services import assistant, groq_client
from tests.test_api import SAMPLE


@pytest.fixture(autouse=True)
def groq_key(monkeypatch):
    monkeypatch.setattr(get_settings(), "groq_api_key", "gsk_test")


@pytest.fixture()
def seeded(client, officer_headers):
    """Make sure at least one stored forecast exists, with SHAP factors."""
    r = client.post("/predictions/predict", json={"items": [SAMPLE]}, headers=officer_headers)
    assert r.status_code == 200
    return r.json()[0]


def fake_chat(captured):
    async def _chat(messages, **kwargs):
        captured.append(messages)
        return "Canned answer."
    return _chat


def test_prediction_includes_shap_factors(seeded):
    factors = seeded["top_factors"]
    assert len(factors) == 5 and {"feature", "value", "impact"} <= set(factors[0])


def test_ask_sends_grounded_context(client, officer_headers, seeded, monkeypatch):
    captured = []
    monkeypatch.setattr(groq_client, "chat", fake_chat(captured))
    r = client.post("/assistant/ask", json={"question": "Why is Ward 17 predicted as high risk?"}, headers=officer_headers)
    assert r.status_code == 200 and r.json()["answer"] == "Canned answer."
    user_msg = captured[0][1]["content"]
    assert "Ward 17: risk" in user_msg and "Factors for this ward" in user_msg
    assert "Why is Ward 17" in user_msg
    assert "Never invent" in captured[0][0]["content"]


def test_daily_plan_and_report_and_explain(client, officer_headers, seeded, monkeypatch):
    captured = []
    monkeypatch.setattr(groq_client, "chat", fake_chat(captured))
    assert client.post("/assistant/daily-plan", json={"available_trucks": 6}, headers=officer_headers).status_code == 200
    assert "Trucks available: 6" in captured[-1][1]["content"]
    assert client.post("/assistant/executive-report", json={}, headers=officer_headers).status_code == 200
    assert client.get("/assistant/explain/17", headers=officer_headers).status_code == 200


def test_citizen_blocked_and_auth_required(client, citizen_headers):
    assert client.post("/assistant/ask", json={"question": "hello there"}, headers=citizen_headers).status_code == 403
    assert client.post("/assistant/ask", json={"question": "hello there"}).status_code == 401


def test_question_validation(client, officer_headers):
    assert client.post("/assistant/ask", json={"question": "x" * 1001}, headers=officer_headers).status_code == 422


def test_not_configured_returns_503(client, officer_headers, seeded, monkeypatch):
    monkeypatch.setattr(get_settings(), "groq_api_key", None)
    r = client.post("/assistant/ask", json={"question": "Explain today's predictions"}, headers=officer_headers)
    assert r.status_code == 503


def test_upstream_failure_returns_502(client, officer_headers, seeded, monkeypatch):
    async def boom(messages, **kwargs):
        raise groq_client.AssistantUpstreamError("down")
    monkeypatch.setattr(groq_client, "chat", boom)
    r = client.post("/assistant/ask", json={"question": "Explain today's predictions"}, headers=officer_headers)
    assert r.status_code == 502


def test_build_context_requires_forecasts():
    with pytest.raises(assistant.NoForecasts):
        assistant.build_context([])


def test_detect_ward():
    assert assistant.detect_ward("Why is ward 17 high risk?") == 17
    assert assistant.detect_ward("Ward#5 please") == 5
    assert assistant.detect_ward("which wards need trucks") is None


def _call(handler, **kw):
    return asyncio.run(groq_client.chat([{"role": "user", "content": "hi"}],
                                        transport=httpx.MockTransport(handler), backoff=0, **kw))


def test_groq_client_parses_reply_and_sends_auth():
    seen = {}

    def handler(request):
        seen["auth"] = request.headers["authorization"]
        seen["path"] = request.url.path
        return httpx.Response(200, json={"choices": [{"message": {"content": " Hello "}}]})

    assert _call(handler) == "Hello"
    assert seen["auth"] == "Bearer gsk_test" and seen["path"].endswith("/chat/completions")


def test_groq_client_retries_then_succeeds():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(429, headers={"retry-after": "0"})
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    assert _call(handler) == "ok" and calls["n"] == 3


def test_groq_client_gives_up_and_does_not_leak_body():
    def handler(request):
        return httpx.Response(401, text="invalid key details")

    with pytest.raises(groq_client.AssistantUpstreamError) as exc:
        _call(handler)
    assert "invalid key" not in str(exc.value)
