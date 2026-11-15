import pytest
from datetime import datetime, UTC
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.tracking_crud import (
    TrackingUserCRUD,
    TrackingClickCRUD,
    TrackingCampaignCRUD,
    TrackingLogCRUD,
)


@pytest.mark.asyncio
class TestTrackingUserCRUD:
    async def test_generate_uuid(self):
        uuid1 = TrackingUserCRUD.generate_uuid()
        uuid2 = TrackingUserCRUD.generate_uuid()

        assert uuid1 is not None
        assert uuid2 is not None
        assert uuid1 != uuid2
        assert len(uuid1) == 36

    async def test_create_user(self, db_session: AsyncSession):
        user = await TrackingUserCRUD.create_or_update(
            session=db_session, telegram_id=123456789, acquisition_source="ad_xcom_nov2025_123"
        )

        assert user is not None
        assert user.telegram_id == 123456789
        assert user.acquisition_source == "ad_xcom_nov2025_123"
        assert user.user_uuid is not None
        assert len(user.user_uuid) == 36

    async def test_upsert_organic_to_ad(self, db_session: AsyncSession):

        user1 = await TrackingUserCRUD.create_or_update(
            session=db_session, telegram_id=987654321, acquisition_source="organic"
        )

        assert user1.acquisition_source == "organic"
        uuid1 = user1.user_uuid

        user2 = await TrackingUserCRUD.create_or_update(
            session=db_session, telegram_id=987654321, acquisition_source="ad_xcom_test_001"
        )

        assert user2.user_uuid == uuid1

        assert user2.acquisition_source == "ad_xcom_test_001"

    async def test_upsert_ad_to_ad_no_change(self, db_session: AsyncSession):

        user1 = await TrackingUserCRUD.create_or_update(
            session=db_session, telegram_id=111222333, acquisition_source="ad_xcom_campaign1"
        )

        original_source = user1.acquisition_source

        user2 = await TrackingUserCRUD.create_or_update(
            session=db_session, telegram_id=111222333, acquisition_source="ad_telegram_campaign2"
        )

        assert user2.acquisition_source == original_source

    async def test_get_by_telegram_id(self, db_session: AsyncSession):

        await TrackingUserCRUD.create_or_update(
            session=db_session, telegram_id=555666777, acquisition_source="organic"
        )

        user = await TrackingUserCRUD.get_by_telegram_id(session=db_session, telegram_id=555666777)

        assert user is not None
        assert user.telegram_id == 555666777

    async def test_get_by_uuid(self, db_session: AsyncSession):

        created_user = await TrackingUserCRUD.create_or_update(
            session=db_session, telegram_id=888999000, acquisition_source="organic"
        )

        uuid_to_find = created_user.user_uuid

        user = await TrackingUserCRUD.get_by_uuid(session=db_session, user_uuid=uuid_to_find)

        assert user is not None
        assert user.user_uuid == uuid_to_find
        assert user.telegram_id == 888999000


@pytest.mark.asyncio
class TestTrackingClickCRUD:
    async def test_create_click(self, db_session: AsyncSession):

        user = await TrackingUserCRUD.create_or_update(
            session=db_session, telegram_id=123123123, acquisition_source="ad_test_001"
        )

        click = await TrackingClickCRUD.create(
            session=db_session,
            user_uuid=user.user_uuid,
            source=user.acquisition_source,
            page="1",
            exchange="binance",
            ip_address="127.0.0.1",
            user_agent="Mozilla/5.0",
            ref_code="TEST123",
        )

        assert click is not None
        assert click.user_uuid == user.user_uuid
        assert click.exchange == "binance"
        assert click.page == "1"
        assert click.ip_address == "127.0.0.1"

    async def test_batch_create_clicks(self, db_session: AsyncSession):

        user1 = await TrackingUserCRUD.create_or_update(
            session=db_session, telegram_id=111111, acquisition_source="organic"
        )

        user2 = await TrackingUserCRUD.create_or_update(
            session=db_session, telegram_id=222222, acquisition_source="ad_xcom_001"
        )

        # Batch insert
        clicks_data = [
            {
                "user_uuid": user1.user_uuid,
                "source": user1.acquisition_source,
                "page": "1",
                "exchange": "binance",
            },
            {
                "user_uuid": user2.user_uuid,
                "source": user2.acquisition_source,
                "page": "2",
                "exchange": "bybit",
            },
        ]

        count = await TrackingClickCRUD.batch_create(session=db_session, clicks_data=clicks_data)

        assert count == 2

    async def test_get_by_user(self, db_session: AsyncSession):

        user = await TrackingUserCRUD.create_or_update(
            session=db_session, telegram_id=333333, acquisition_source="organic"
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

        clicks = await TrackingClickCRUD.get_by_user(session=db_session, user_uuid=user.user_uuid)

        assert len(clicks) == 2


@pytest.mark.asyncio
class TestTrackingCampaignCRUD:
    async def test_create_campaign(self, db_session: AsyncSession):
        campaign = await TrackingCampaignCRUD.create_or_update(
            session=db_session,
            campaign_id="nov2025_123",
            platform="xcom",
            description="Test campaign",
        )

        assert campaign is not None
        assert campaign.campaign_id == "nov2025_123"
        assert campaign.platform == "xcom"
        assert campaign.total_users == 0
        assert campaign.total_clicks == 0

    async def test_upsert_campaign(self, db_session: AsyncSession):

        campaign1 = await TrackingCampaignCRUD.create_or_update(
            session=db_session,
            campaign_id="test_campaign",
            platform="xcom",
            description="Original description",
        )

        campaign2 = await TrackingCampaignCRUD.create_or_update(
            session=db_session,
            campaign_id="test_campaign",
            platform="telegram_ads",
            description="Updated description",
        )

        assert campaign1.id == campaign2.id
        assert campaign2.platform == "telegram_ads"
        assert campaign2.description == "Updated description"

    async def test_increment_users(self, db_session: AsyncSession):
        campaign = await TrackingCampaignCRUD.create_or_update(
            session=db_session, campaign_id="increment_test", platform="xcom"
        )

        assert campaign.total_users == 0

        await TrackingCampaignCRUD.increment_users(session=db_session, campaign_id="increment_test")

        updated_campaign = await TrackingCampaignCRUD.get_by_id(
            session=db_session, campaign_id="increment_test"
        )

        assert updated_campaign.total_users == 1

    async def test_get_all_active(self, db_session: AsyncSession):

        await TrackingCampaignCRUD.create_or_update(
            session=db_session, campaign_id="active_campaign", platform="xcom", end_date=None
        )

        active_campaigns = await TrackingCampaignCRUD.get_all_active(session=db_session)

        assert len(active_campaigns) >= 1
        assert any(c.campaign_id == "active_campaign" for c in active_campaigns)


@pytest.mark.asyncio
class TestTrackingLogCRUD:
    async def test_create_log(self, db_session: AsyncSession):
        log = await TrackingLogCRUD.create(
            session=db_session,
            event_type="error",
            message="Test error message",
            context={"test": "data"},
        )

        assert log is not None
        assert log.event_type == "error"
        assert log.message == "Test error message"
        assert log.context == {"test": "data"}

    async def test_get_recent_logs(self, db_session: AsyncSession):

        await TrackingLogCRUD.create(
            session=db_session, event_type="info", message="Info message 1"
        )

        await TrackingLogCRUD.create(
            session=db_session, event_type="warning", message="Warning message"
        )

        all_logs = await TrackingLogCRUD.get_recent(session=db_session, limit=10)

        assert len(all_logs) >= 2

        warning_logs = await TrackingLogCRUD.get_recent(
            session=db_session, event_type="warning", limit=10
        )

        assert len(warning_logs) >= 1
        assert all(log.event_type == "warning" for log in warning_logs)
