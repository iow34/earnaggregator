"""
Section 3.3 - Metrics endpoint tests.

Verifies that /metrics returns Prometheus text format and key metric names exist.
"""

import pytest
import httpx

from app.main import app

pytestmark = pytest.mark.asyncio


async def test_metrics_endpoint_prometheus_text():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/metrics")
        assert resp.status_code == 200
        ctype = resp.headers.get("content-type", "")
        assert "text/plain" in ctype
        body = resp.text
        # Basic sanity checks for Prometheus exposition format
        assert "# HELP" in body or "# TYPE" in body
        # Typical builtin metric names
        assert "python_gc_collections_total" in body or "process_virtual_memory_bytes" in body
