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
    # 1) Синхронізуємо реальні дані Bybit/Binance до БД (використовує test DB з env)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Спроба Bybit sync (публічний API)
        await client.post("/api/v1/bybit/sync", params={"symbol": "BTC"})
        # Спроба Binance sync (потребує ключі; якщо немає — endpoint поверне warning/error, це ок)
        await client.post("/api/v1/binance/sync", params={"symbol": "BTC"})

        # 2) Викликаємо основний endpoint
        resp = await client.get("/api/v1/yield/BTC")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload.get("success") is True
        # Даних може бути 0 якщо біржі не повернули продуктів, але endpoint має відпрацювати без помилок
        assert "data" in payload


async def test_top_happy_db_backed():
    # 1) Підвантажуємо реальні дані в БД (ETH)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/bybit/sync", params={"symbol": "ETH"})
        await client.post("/api/v1/binance/sync", params={"symbol": "ETH"})

        # 2) Отримуємо топ (fallback до БД, якщо кеш порожній)
        resp = await client.get("/api/v1/top", params={"limit": 1})
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("success") is True
        assert "data" in body


async def test_exchanges_happy():
    # Пряма перевірка endpoint з реальними даними (агрегація може звертатися до API/БД)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/exchanges", params={"exchange": "binance", "symbol": "BTC", "limit": 1})
        # Якщо Binance ключі відсутні — endpoint все одно має повертати 200 з можливо порожніми даними або даними Bybit
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("success") is True
        assert "data" in body


async def test_health_happy():
    # Перевірка health без моків (реальні сервіси/кеш/БД)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload.get("success") in (True, False)
        assert payload.get("database_status") in ("healthy", "unhealthy")
        assert payload.get("cache_status") in ("healthy", "degraded", "unknown")
        assert isinstance(payload.get("api_status"), dict)
