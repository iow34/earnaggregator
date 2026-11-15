"""
Section 3.1 - API routes basic happy-path tests.

Covers:
- GET /api/v1/yield/{symbol}
- GET /api/v1/top
- GET /api/v1/exchanges
- GET /api/v1/health

Tests mock aggregation/cache/db/exchange services to avoid external deps.
"""

import asyncio
import pytest
import httpx

from app.main import app


pytestmark = pytest.mark.asyncio


async def test_yield_symbol_happy():

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post("/api/v1/bybit/sync", params={"symbol": "BTC"})

        await client.post("/api/v1/binance/sync", params={"symbol": "BTC"})

        resp = await client.get("/api/v1/yield/BTC")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload.get("success") is True

        assert "data" in payload


async def test_top_happy_db_backed():

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post("/api/v1/bybit/sync", params={"symbol": "ETH"})
        await client.post("/api/v1/binance/sync", params={"symbol": "ETH"})

        resp = await client.get("/api/v1/top", params={"limit": 1})
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("success") is True
        assert "data" in body


async def test_exchanges_happy():

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v1/exchanges", params={"exchange": "binance", "symbol": "BTC", "limit": 1}
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body.get("success") is True
        assert "data" in body


async def test_health_happy():

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload.get("success") in (True, False)
        assert payload.get("database_status") in ("healthy", "unhealthy")
        assert payload.get("cache_status") in ("healthy", "degraded", "unknown")
        assert isinstance(payload.get("api_status"), dict)
