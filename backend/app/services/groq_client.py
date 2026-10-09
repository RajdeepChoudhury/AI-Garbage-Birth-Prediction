"""Minimal async client for Groq's OpenAI compatible chat completions API."""
import asyncio
import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
RETRYABLE = {429, 500, 502, 503, 504}


class AssistantNotConfigured(Exception):
    """GROQ_API_KEY is missing."""


class AssistantUpstreamError(Exception):
    """Groq failed or refused the request after retries."""


async def chat(
    messages: list[dict],
    *,
    transport: httpx.AsyncBaseTransport | None = None,
    attempts: int = 3,
    backoff: float = 0.5,
) -> str:
    s = get_settings()
    if not s.groq_api_key:
        raise AssistantNotConfigured("GROQ_API_KEY is not set")

    payload = {
        "model": s.groq_model,
        "messages": messages,
        "temperature": s.groq_temperature,
        "max_tokens": s.groq_max_tokens,
    }
    headers = {"Authorization": f"Bearer {s.groq_api_key}"}

    async with httpx.AsyncClient(base_url=s.groq_base_url, timeout=s.groq_timeout, transport=transport) as client:
        for attempt in range(attempts):
            last = attempt == attempts - 1
            try:
                resp = await client.post("/chat/completions", json=payload, headers=headers)
            except httpx.HTTPError as exc:
                logger.warning("Groq request error (%s), attempt %d", type(exc).__name__, attempt + 1)
                if last:
                    raise AssistantUpstreamError("Could not reach Groq") from exc
                await asyncio.sleep(backoff * 2**attempt)
                continue

            if resp.status_code in RETRYABLE and not last:
                wait = min(float(resp.headers.get("retry-after", backoff * 2**attempt)), 5.0)
                logger.warning("Groq returned %d, retrying in %.1fs", resp.status_code, wait)
                await asyncio.sleep(wait if backoff else 0)
                continue
            if resp.status_code >= 400:
                logger.error("Groq error %d: %s", resp.status_code, resp.text[:300])
                raise AssistantUpstreamError(f"Groq returned status {resp.status_code}")

            try:
                return resp.json()["choices"][0]["message"]["content"].strip()
            except (KeyError, IndexError, ValueError) as exc:
                raise AssistantUpstreamError("Unexpected response format from Groq") from exc
    raise AssistantUpstreamError("Groq request failed")
