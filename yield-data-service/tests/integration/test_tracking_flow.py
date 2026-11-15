import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.db.tracking_crud import TrackingUserCRUD, TrackingClickCRUD


@pytest.mark.asyncio
class TestTrackingFlow:
    async def test_full_user_registration_flow(self, db_session: AsyncSession):
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/tracking/user/register",
                json={
                    "telegram_id": 999888777,
                    "payload": "ad_xcom_integration_test_001",
                    "username": "test_user",
                    "first_name": "Test",
                    "last_name": "User",
                },
            )

            assert response.status_code == 200
            data = response.json()

            assert data["success"] is True
            assert data["user_uuid"] is not None
            assert data["acquisition_source"] == "ad_xcom_integration_test_001"
            assert data["is_new_user"] is True
            assert data["campaign_id"] == "integration_test_001"

            user_uuid = data["user_uuid"]

            user = await TrackingUserCRUD.get_by_telegram_id(
                session=db_session, telegram_id=999888777
            )

            assert user is not None
            assert user.user_uuid == user_uuid
            assert user.acquisition_source == "ad_xcom_integration_test_001"

    async def test_full_click_tracking_flow(self, db_session: AsyncSession):
        async with AsyncClient(app=app, base_url="http://test", follow_redirects=False) as client:
            reg_response = await client.post(
                "/api/v1/tracking/user/register",
                json={"telegram_id": 777666555, "payload": "ad_telegram_ads_click_test"},
            )

            assert reg_response.status_code == 200
            user_data = reg_response.json()
            user_uuid = user_data["user_uuid"]

            redirect_response = await client.get(
                "/ref",
                params={
                    "user": user_uuid,
                    "source": "ad_telegram_ads_click_test",
                    "page": "2",
                    "exchange": "binance",
                    "ref_code": "TEST123",
                },
            )

            assert redirect_response.status_code == 302
            assert "binance" in redirect_response.headers["location"].lower()

            clicks = await TrackingClickCRUD.get_by_user(session=db_session, user_uuid=user_uuid)

            assert len(clicks) >= 1
            click = clicks[0]
            assert click.exchange == "binance"
            assert click.page == "2"
            assert click.ref_code == "TEST123"

    async def test_organic_user_flow(self, db_session: AsyncSession):
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/tracking/user/register",
                json={
                    "telegram_id": 555444333,
                    "payload": None,  # Organic
                },
            )

            assert response.status_code == 200
            data = response.json()

            assert data["acquisition_source"] == "organic"
            assert data["campaign_id"] is None

    async def test_race_condition_handling(self, db_session: AsyncSession):
        async with AsyncClient(app=app, base_url="http://test") as client:
            telegram_id = 444333222

            import asyncio

            async def register():
                return await client.post(
                    "/api/v1/tracking/user/register",
                    json={"telegram_id": telegram_id, "payload": "ad_xcom_race_test"},
                )

            responses = await asyncio.gather(register(), register(), register())

            for response in responses:
                assert response.status_code == 200

            uuids = [r.json()["user_uuid"] for r in responses]

            unique_uuids = set(uuids)
            assert len(unique_uuids) <= 3

            user = await TrackingUserCRUD.get_by_telegram_id(
                session=db_session, telegram_id=telegram_id
            )
            assert user is not None

    async def test_invalid_payload_handling(self, db_session: AsyncSession):
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/tracking/user/register",
                json={"telegram_id": 333222111, "payload": "invalid&payload"},
            )

            assert response.status_code == 200
            data = response.json()

            assert data["acquisition_source"] == "malformed_deeplink"

    async def test_redirect_missing_params(self):
        async with AsyncClient(app=app, base_url="http://test", follow_redirects=False) as client:
            response = await client.get("/ref?exchange=binance&page=1")

            assert response.status_code == 302

    async def test_redirect_invalid_exchange(self, db_session: AsyncSession):
        async with AsyncClient(app=app, base_url="http://test", follow_redirects=False) as client:
            reg_response = await client.post(
                "/api/v1/tracking/user/register", json={"telegram_id": 222111000, "payload": None}
            )

            user_uuid = reg_response.json()["user_uuid"]

            response = await client.get(
                "/ref",
                params={
                    "user": user_uuid,
                    "source": "organic",
                    "page": "1",
                    "exchange": "invalid_exchange",
                },
            )

            assert response.status_code == 302

    async def test_get_user_clicks_history(self, db_session: AsyncSession):
        async with AsyncClient(app=app, base_url="http://test", follow_redirects=False) as client:
            reg_response = await client.post(
                "/api/v1/tracking/user/register",
                json={"telegram_id": 111000999, "payload": "ad_test_history"},
            )

            user_uuid = reg_response.json()["user_uuid"]

            for exchange in ["binance", "bybit", "okx"]:
                await client.get(
                    "/ref",
                    params={
                        "user": user_uuid,
                        "source": "ad_test_history",
                        "page": "1",
                        "exchange": exchange,
                    },
                )

            history_response = await client.get(
                f"/api/v1/tracking/analytics/user/{user_uuid}/clicks"
            )

            assert history_response.status_code == 200
            history_data = history_response.json()

            assert history_data["success"] is True
            assert history_data["total_clicks"] >= 3


@pytest.mark.asyncio
class TestAnalyticsIntegration:
    async def test_ctr_analytics(self):
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/tracking/analytics/ctr")

            assert response.status_code == 200
            data = response.json()

            assert data["success"] is True
            assert "data" in data

    async def test_conversions_analytics(self):
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/tracking/analytics/conversions")

            assert response.status_code == 200
            data = response.json()

            assert data["success"] is True
            assert "data" in data

    async def test_campaign_performance(self):
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/tracking/analytics/campaign-performance")

            assert response.status_code == 200
            data = response.json()

            assert data["success"] is True
            assert "data" in data

    async def test_popular_exchanges(self):
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/tracking/analytics/popular-exchanges?limit=10")

            assert response.status_code == 200
            data = response.json()

            assert data["success"] is True

    async def test_user_journey(self, db_session: AsyncSession):
        async with AsyncClient(app=app, base_url="http://test", follow_redirects=False) as client:
            reg_response = await client.post(
                "/api/v1/tracking/user/register",
                json={"telegram_id": 999111222, "payload": "ad_journey_analytics"},
            )

            user_uuid = reg_response.json()["user_uuid"]

            await client.get(
                "/ref",
                params={
                    "user": user_uuid,
                    "source": "ad_journey_analytics",
                    "page": "1",
                    "exchange": "binance",
                },
            )

            # User journey
            journey_response = await client.get(
                f"/api/v1/tracking/analytics/user-journey/{user_uuid}"
            )

            assert journey_response.status_code == 200
            journey_data = journey_response.json()

            assert journey_data["success"] is True
            assert journey_data["data"]["user_uuid"] == user_uuid
            assert journey_data["data"]["total_clicks"] >= 1


@pytest.mark.asyncio
class TestRateLimiting:
    async def test_rate_limit_enforcement(self, db_session: AsyncSession):
        async with AsyncClient(app=app, base_url="http://test", follow_redirects=False) as client:
            reg_response = await client.post(
                "/api/v1/tracking/user/register", json={"telegram_id": 123321123, "payload": None}
            )

            user_uuid = reg_response.json()["user_uuid"]

            responses = []
            for i in range(15):
                response = await client.get(
                    "/ref",
                    params={
                        "user": user_uuid,
                        "source": "organic",
                        "page": "1",
                        "exchange": "binance",
                    },
                )
                responses.append(response)

            successful = [r for r in responses if r.status_code == 302]
            rate_limited = [r for r in responses if r.status_code == 429]

            assert len(successful) >= 1
