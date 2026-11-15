import os
from pathlib import Path
import sys

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/earn_test")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "yield-data-service"))

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from app.api.dependencies import protect_operations, require_service_key
from app.config import settings


def test_operational_authorization_fails_closed(monkeypatch):
    app = FastAPI()
    app.get("/api/v1/products", dependencies=[Depends(protect_operations)])(lambda: {"ok": True})
    app.post("/api/v1/cache/clear", dependencies=[Depends(protect_operations)])(
        lambda: {"ok": True}
    )
    app.get("/api/v1/tracking/user/1", dependencies=[Depends(require_service_key)])(
        lambda: {"ok": True}
    )
    app.get("/api/v1/binance/test", dependencies=[Depends(protect_operations)])(
        lambda: {"ok": True}
    )
    client = TestClient(app)
    monkeypatch.setattr(settings, "service_api_key", "")
    assert client.post("/api/v1/cache/clear").status_code == 503
    assert client.get("/api/v1/products").status_code == 200
    monkeypatch.setattr(settings, "service_api_key", "unit-test-service-key")
    assert client.post("/api/v1/cache/clear").status_code == 401
    assert client.get("/api/v1/tracking/user/1").status_code == 401
    assert client.get("/api/v1/binance/test").status_code == 401
    assert (
        client.post("/api/v1/cache/clear", headers={"X-Service-API-Key": "wrong"}).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/cache/clear", headers={"X-Service-API-Key": "unit-test-service-key"}
        ).status_code
        == 200
    )


def test_real_app_keeps_mutations_private_and_has_no_migration_route(monkeypatch):
    from app.main import app

    monkeypatch.setattr(settings, "service_api_key", "unit-test-service-key")
    # No lifespan: denied requests must fail before touching storage or exchanges.
    client = TestClient(app)
    assert client.post("/api/v1/cache/clear").status_code == 401
    assert client.post("/api/v1/scheduler/trigger/sync").status_code == 401
    assert client.get("/api/v1/tracking/user/1").status_code == 401
    assert client.post("/api/v1/migrations/run").status_code == 404
