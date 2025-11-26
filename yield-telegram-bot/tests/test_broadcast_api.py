"""
Тести для FastAPI endpoint створення розсилки.
"""

from typing import Optional

import pytest
from fastapi import FastAPI, Header, HTTPException
from httpx import AsyncClient, ASGITransport

from bot.broadcasts.api import (
    router,
    get_broadcast_service,
    get_current_admin,
    get_db_session,
)


class DummyAdmin:
    id = 1
    role = "operator"


class OwnerAdmin(DummyAdmin):
    id = 2
    role = "owner"


class DummyService:
    async def list_broadcasts(self, **kwargs):
        summary = {
            "id": 1,
            "title": "Demo",
            "status": "queued",
            "channel": "web_ui",
            "total_recipients": 10,
            "stats": {"sent": 5, "failed": 0, "pending": 5, "skipped": 0},
            "requires_approval": False,
            "scheduled_at": None,
            "started_at": None,
            "completed_at": None,
            "created_at": "2025-11-24T00:00:00Z",
            "updated_at": "2025-11-24T00:00:00Z",
            "author": {"id": 1, "email": "test@example.com", "role": "operator"},
        }
        return {"items": [summary], "page": 1, "per_page": 20, "total": 1}

    async def create_broadcast(self, session, payload, admin):
        return {"broadcast_id": 1, "status": "draft", "title": payload.title}

    async def get_status(self, session, broadcast_id: int):
        return {"broadcast_id": broadcast_id, "status": "queued"}

    async def get_broadcast_detail(self, session, broadcast_id: int):
        summary = {
            "id": broadcast_id,
            "title": "Demo",
            "status": "queued",
            "channel": "web_ui",
            "total_recipients": 10,
            "stats": {"sent": 5, "failed": 0, "pending": 5, "skipped": 0},
            "requires_approval": False,
            "scheduled_at": None,
            "started_at": None,
            "completed_at": None,
            "created_at": "2025-11-24T00:00:00Z",
            "updated_at": "2025-11-24T00:00:00Z",
            "author": {"id": 1, "email": "test@example.com", "role": "operator"},
        }
        return {
            "broadcast": summary,
            "content": {"text": "Hello", "parse_mode": "HTML", "buttons": []},
            "filters": {"languages": ["ua"], "tags_all": [], "tags_any": [], "telegram_ids": [], "is_subscribed": True},
            "metadata": {},
            "preview_chat_id": None,
            "batch_size": 100,
        }

    async def cancel_broadcast(self, session, broadcast_id: int, admin):
        return {"broadcast_id": broadcast_id, "status": "cancelled"}

    async def retry_broadcast(self, session, broadcast_id: int, admin):
        return {"broadcast_id": broadcast_id, "status": "requeued"}

    async def get_broadcast_events(self, session, broadcast_id: int, page: int, per_page: int):
        return {
            "items": [
                {
                    "id": 1,
                    "event_type": "created",
                    "payload": {},
                    "created_at": "2025-11-24T00:00:00Z",
                    "admin": {"id": 1, "email": "test@example.com", "role": "operator"},
                }
            ],
            "page": page,
            "per_page": per_page,
            "total": 1,
        }

    async def get_broadcast_recipients(self, session, broadcast_id: int, status, page: int, per_page: int, search: Optional[str]):
        return {
            "items": [
                {
                    "id": 1,
                    "telegram_id": 123,
                    "language": "ua",
                    "status": "sent",
                    "attempts": 1,
                    "message_id": "42",
                    "error_code": None,
                    "last_attempt_at": "2025-11-24T00:00:00Z",
                    "created_at": "2025-11-24T00:00:00Z",
                }
            ],
            "page": page,
            "per_page": per_page,
            "total": 1,
        }

    async def get_dashboard_metrics(self, session):
        return {
            "total_broadcasts": 10,
            "active_broadcasts": 2,
            "scheduled_broadcasts": 3,
            "pending_approval": 1,
            "sent_today": 500,
            "failed_today": 5,
        }

    async def send_preview(self, payload, admin):
        return {"preview_chat_id": payload.preview_chat_id, "status": "sent"}

    async def approve_broadcast(self, session, broadcast_id: int, admin):
        if admin.role != "owner":
            raise PermissionError("Owner role required")
        return {"broadcast_id": broadcast_id, "status": "queued"}


@pytest.fixture
def api_app():
    app = FastAPI()
    app.include_router(router)

    async def fake_admin(x_admin_api_key: str = Header(default=None)):
        if not x_admin_api_key:
            raise HTTPException(status_code=401, detail="API key required")
        return DummyAdmin()

    async def fake_session():
        yield object()

    app.dependency_overrides[get_current_admin] = fake_admin
    app.dependency_overrides[get_db_session] = fake_session
    app.dependency_overrides[get_broadcast_service] = lambda: DummyService()
    app.state.default_admin_override = fake_admin
    return app


@pytest.mark.asyncio
async def test_create_broadcast_requires_api_key(api_app):
    transport = ASGITransport(app=api_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/broadcasts",
            json={
                "title": "No key",
                "content_type": "text",
                "content": {"text": "hi"},
                "filters": {},
            },
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_broadcasts(api_app):
    transport = ASGITransport(app=api_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/broadcasts", headers={"x-admin-api-key": "test"})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["stats"]["pending"] == 5


@pytest.mark.asyncio
async def test_create_broadcast_success(api_app):
    transport = ASGITransport(app=api_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/broadcasts",
            headers={"x-admin-api-key": "test"},
            json={
                "title": "Weekly update",
                "content_type": "text",
                "content": {"text": "Hello"},
                "filters": {"languages": ["ua"]},
            },
        )
        assert response.status_code == 201
        assert response.json()["broadcast_id"] == 1


@pytest.mark.asyncio
async def test_get_broadcast_status(api_app):
    transport = ASGITransport(app=api_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/broadcasts/1/status", headers={"x-admin-api-key": "test"})
        assert response.status_code == 200
        assert response.json()["status"] == "queued"


@pytest.mark.asyncio
async def test_get_broadcast_detail(api_app):
    transport = ASGITransport(app=api_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/broadcasts/1", headers={"x-admin-api-key": "test"})
        assert response.status_code == 200
        assert response.json()["broadcast"]["id"] == 1


@pytest.mark.asyncio
async def test_cancel_broadcast(api_app):
    transport = ASGITransport(app=api_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/broadcasts/1/cancel",
            headers={"x-admin-api-key": "test"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_retry_broadcast(api_app):
    transport = ASGITransport(app=api_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/broadcasts/1/retry",
            headers={"x-admin-api-key": "test"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "requeued"


@pytest.mark.asyncio
async def test_preview_endpoint(api_app):
    transport = ASGITransport(app=api_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/broadcasts/preview",
            headers={"x-admin-api-key": "test"},
            json={
                "preview_chat_id": 123,
                "content_type": "text",
                "content": {"text": "Hello preview"},
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == "sent"


@pytest.mark.asyncio
async def test_approve_requires_owner(api_app):
    transport = ASGITransport(app=api_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/broadcasts/1/approve",
            headers={"x-admin-api-key": "test"},
        )
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_approve_broadcast_success(api_app):
    async def fake_owner(x_admin_api_key: str = Header(default=None)):
        if not x_admin_api_key:
            raise HTTPException(status_code=401, detail="API key required")
        return OwnerAdmin()

    api_app.dependency_overrides[get_current_admin] = fake_owner

    transport = ASGITransport(app=api_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/broadcasts/1/approve",
            headers={"x-admin-api-key": "test"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "queued"

    api_app.dependency_overrides[get_current_admin] = api_app.state.default_admin_override


@pytest.mark.asyncio
async def test_list_broadcast_events(api_app):
    transport = ASGITransport(app=api_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/broadcasts/1/events", headers={"x-admin-api-key": "test"})
        assert response.status_code == 200
        assert response.json()["items"][0]["event_type"] == "created"


@pytest.mark.asyncio
async def test_list_broadcast_recipients(api_app):
    transport = ASGITransport(app=api_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/broadcasts/1/recipients", headers={"x-admin-api-key": "test"})
        assert response.status_code == 200
        assert response.json()["items"][0]["status"] == "sent"


@pytest.mark.asyncio
async def test_metrics_summary(api_app):
    transport = ASGITransport(app=api_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/broadcasts/metrics/summary", headers={"x-admin-api-key": "test"})
        assert response.status_code == 200
        assert response.json()["total_broadcasts"] == 10

