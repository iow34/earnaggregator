import pytest
from datetime import datetime, UTC
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.tracking_crud import TrackingUserCRUD, TrackingClickCRUD, TrackingCampaignCRUD
from app.services.tracking.analytics import tracking_analytics


@pytest.mark.asyncio
class TestTrackingAnalytics:
    async def test_ctr_calculation(self, db_session: AsyncSession):

        user1 = await TrackingUserCRUD.create_or_update(
            session=db_session, telegram_id=11111, acquisition_source="test_ctr_001"
        )

        user2 = await TrackingUserCRUD.create_or_update(
            session=db_session, telegram_id=22222, acquisition_source="test_ctr_001"
        )

        for _ in range(3):
            await TrackingClickCRUD.create(
                session=db_session,
                user_uuid=user1.user_uuid,
                source=user1.acquisition_source,
                page="1",
                exchange="binance",
            )

        await TrackingClickCRUD.create(
            session=db_session,
            user_uuid=user2.user_uuid,
            source=user2.acquisition_source,
            page="1",
            exchange="bybit",
        )

        ctr_data = await tracking_analytics.get_ctr_by_pages(session=db_session)

        page1_ctr = next((p for p in ctr_data if p["page"] == "1"), None)

        assert page1_ctr is not None
        assert page1_ctr["total_clicks"] >= 4
        assert page1_ctr["unique_users"] >= 2
        # CTR = 4 clicks / 2 users = 2.0
        assert page1_ctr["ctr"] >= 2.0

    async def test_conversion_rate(self, db_session: AsyncSession):

        user1 = await TrackingUserCRUD.create_or_update(
            session=db_session, telegram_id=11001, acquisition_source="test_conv_001"
        )

        await TrackingUserCRUD.create_or_update(
            session=db_session, telegram_id=11002, acquisition_source="test_conv_001"
        )

        await TrackingUserCRUD.create_or_update(
            session=db_session, telegram_id=11003, acquisition_source="test_conv_001"
        )

        await TrackingClickCRUD.create(
            session=db_session,
            user_uuid=user1.user_uuid,
            source=user1.acquisition_source,
            page="1",
            exchange="binance",
        )

        conversion_data = await tracking_analytics.get_conversion_rate(
            session=db_session, source_pattern="test_conv_%"
        )

        assert conversion_data["total_users"] >= 3
        assert conversion_data["users_with_clicks"] >= 1

    async def test_popular_exchanges(self, db_session: AsyncSession):

        user = await TrackingUserCRUD.create_or_update(
            session=db_session, telegram_id=99001, acquisition_source="test_popular"
        )

        await TrackingClickCRUD.create(
            session=db_session,
            user_uuid=user.user_uuid,
            source=user.acquisition_source,
            page="1",
            exchange="binance",
        )

        await TrackingClickCRUD.create(
            session=db_session,
            user_uuid=user.user_uuid,
            source=user.acquisition_source,
            page="1",
            exchange="binance",
        )

        await TrackingClickCRUD.create(
            session=db_session,
            user_uuid=user.user_uuid,
            source=user.acquisition_source,
            page="1",
            exchange="bybit",
        )

        popular = await tracking_analytics.get_popular_exchanges(session=db_session, limit=10)

        assert len(popular) >= 2

        binance_data = next((e for e in popular if e["exchange"] == "binance"), None)
        assert binance_data is not None
        assert binance_data["total_clicks"] >= 2

    async def test_user_journey(self, db_session: AsyncSession):

        user = await TrackingUserCRUD.create_or_update(
            session=db_session, telegram_id=88001, acquisition_source="ad_journey_test"
        )

        await TrackingClickCRUD.create(
            session=db_session,
            user_uuid=user.user_uuid,
            source=user.acquisition_source,
            page="1",
            exchange="binance",
        )

        await TrackingClickCRUD.create(
            session=db_session,
            user_uuid=user.user_uuid,
            source=user.acquisition_source,
            page="2",
            exchange="bybit",
        )

        journey = await tracking_analytics.get_user_journey(
            session=db_session, user_uuid=user.user_uuid
        )

        assert journey is not None
        assert journey["user_uuid"] == user.user_uuid
        assert journey["total_clicks"] == 2
        assert "binance" in journey["exchanges_clicked"]
        assert "bybit" in journey["exchanges_clicked"]
        assert journey["time_to_first_click_seconds"] is not None


@pytest.mark.asyncio
class TestCampaignPerformance:
    async def test_campaign_performance(self, db_session: AsyncSession):

        campaign = await TrackingCampaignCRUD.create_or_update(
            session=db_session,
            campaign_id="perf_test_001",
            platform="xcom",
            description="Performance test campaign",
        )

        user1 = await TrackingUserCRUD.create_or_update(
            session=db_session, telegram_id=77001, acquisition_source="ad_xcom_perf_test_001"
        )

        await TrackingClickCRUD.create(
            session=db_session,
            user_uuid=user1.user_uuid,
            source=user1.acquisition_source,
            page="1",
            exchange="binance",
        )

        await TrackingCampaignCRUD.increment_users(session=db_session, campaign_id="perf_test_001")

        await TrackingCampaignCRUD.increment_clicks(session=db_session, campaign_id="perf_test_001")

        performance = await tracking_analytics.get_campaign_performance(
            session=db_session, campaign_id="perf_test_001"
        )

        assert len(performance) == 1
        assert performance[0]["campaign_id"] == "perf_test_001"
        assert performance[0]["total_users"] >= 1
        assert performance[0]["total_clicks"] >= 1
