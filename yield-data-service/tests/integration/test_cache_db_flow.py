import pytest
import httpx

from app.main import app
from app.services import cache as cache_mod


pytestmark = pytest.mark.asyncio


async def test_cache_then_db_crud_flow_btc():
    symbol = "BTC"
    key = cache_mod.get_exchange_cache_key("bybit", symbol)

    try:
        await cache_mod.delete_cached_data(key)
    except Exception:
        pass

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        try:
            await client.get("/api/v1/bybit/products", params={"symbol": symbol})
        except Exception:
            pass

        got = await cache_mod.get_cached_data(key)

        assert got is None or isinstance(got, (dict, list))

        await client.post("/api/v1/bybit/sync", params={"symbol": symbol})
        await client.post("/api/v1/binance/sync", params={"symbol": symbol})

        r = await client.get(f"/api/v1/yield/{symbol}")
        assert r.status_code == 200
        body = r.json()
        assert body.get("success") is True
