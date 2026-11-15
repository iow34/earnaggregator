import pytest
from fastapi.testclient import TestClient
from demo.server import create_app


@pytest.fixture
def client():
    with TestClient(create_app()) as client:
        yield client


def test_catalogue_filtering_and_sorting(client):
    result = client.get("/api/v1/products", params={"symbol": "usdt"}).json()
    assert result["source"] == "synthetic-preview"
    assert result["count"] == 2
    assert [p["apy"] for p in result["data"]] == sorted(
        [p["apy"] for p in result["data"]], reverse=True
    )
    assert all(p["symbol"] == "USDT" for p in result["data"])


def test_broadcast_draft_round_trip_without_delivery(client):
    payload = {
        "title": "Release digest",
        "content": {"text": "A new catalogue update"},
        "requires_approval": True,
    }
    response = client.post("/api/broadcasts", json=payload)
    assert response.status_code == 201
    identifier = response.json()["broadcast_id"]
    detail = client.get(f"/api/broadcasts/{identifier}").json()
    assert detail["content"]["text"] == payload["content"]["text"]
    assert detail["broadcast"]["status"] == "draft"
    assert detail["broadcast"]["stats"]["sent"] == 0
    assert detail["broadcast"]["total_recipients"] == 0
    assert client.get("/api/broadcasts/metrics/summary").json()["total_broadcasts"] == 2
    assert client.get("/api/broadcasts", params={"search": "Release"}).json()["total"] == 1


def test_preview_validation_and_isolation(client):
    assert (
        client.post("/api/broadcasts", json={"title": "", "content": {"text": ""}}).status_code
        == 422
    )
    assert client.get("/api/broadcasts", params={"page": 0}).status_code == 422
    assert client.get("/api/broadcasts/999").status_code == 404
    assert TestClient(create_app()).get("/api/broadcasts").json()["total"] == 1
    assert client.get("/health").json()["external_connections"] is False
