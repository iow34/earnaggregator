"""
Unit тести для Tracking CRUD операцій.

Тестує:
- Створення користувачів з UUID
- UPSERT логіку (race conditions)
- Batch insert кліків
- Campaign CRUD
"""

import pytest
from datetime import datetime, UTC
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.tracking_crud import (
    TrackingUserCRUD, TrackingClickCRUD, 
    TrackingCampaignCRUD, TrackingLogCRUD
)


@pytest.mark.asyncio
class TestTrackingUserCRUD:
    """Тести для TrackingUserCRUD."""
    
    async def test_generate_uuid(self):
        """Тест генерації UUID."""
        uuid1 = TrackingUserCRUD.generate_uuid()
        uuid2 = TrackingUserCRUD.generate_uuid()
        
        assert uuid1 is not None
        assert uuid2 is not None
        assert uuid1 != uuid2  # UUID мають бути унікальні
        assert len(uuid1) == 36  # Стандартна довжина UUID
    
    async def test_create_user(self, db_session: AsyncSession):
        """Тест створення нового користувача."""
        user = await TrackingUserCRUD.create_or_update(
            session=db_session,
            telegram_id=123456789,
            acquisition_source="ad_xcom_nov2025_123"
        )
        
        assert user is not None
        assert user.telegram_id == 123456789
        assert user.acquisition_source == "ad_xcom_nov2025_123"
        assert user.user_uuid is not None
        assert len(user.user_uuid) == 36
    
    async def test_upsert_organic_to_ad(self, db_session: AsyncSession):
        """Тест оновлення organic користувача на рекламний."""
        # Створюємо organic користувача
        user1 = await TrackingUserCRUD.create_or_update(
            session=db_session,
            telegram_id=987654321,
            acquisition_source="organic"
        )
        
        assert user1.acquisition_source == "organic"
        uuid1 = user1.user_uuid
        
        # Оновлюємо на рекламний source
        user2 = await TrackingUserCRUD.create_or_update(
            session=db_session,
            telegram_id=987654321,
            acquisition_source="ad_xcom_test_001"
        )
        
        # UUID залишається той самий
        assert user2.user_uuid == uuid1
        # Source оновлюється
        assert user2.acquisition_source == "ad_xcom_test_001"
    
    async def test_upsert_ad_to_ad_no_change(self, db_session: AsyncSession):
        """Тест що рекламний source не перезаписується іншим."""
        # Створюємо користувача з рекламним source
        user1 = await TrackingUserCRUD.create_or_update(
            session=db_session,
            telegram_id=111222333,
            acquisition_source="ad_xcom_campaign1"
        )
        
        original_source = user1.acquisition_source
        
        # Пробуємо оновити іншим рекламним source
        user2 = await TrackingUserCRUD.create_or_update(
            session=db_session,
            telegram_id=111222333,
            acquisition_source="ad_telegram_campaign2"
        )
        
        # Source НЕ змінюється (залишається перший)
        assert user2.acquisition_source == original_source
    
    async def test_get_by_telegram_id(self, db_session: AsyncSession):
        """Тест пошуку користувача за Telegram ID."""
        # Створюємо користувача
        await TrackingUserCRUD.create_or_update(
            session=db_session,
            telegram_id=555666777,
            acquisition_source="organic"
        )
        
        # Шукаємо
        user = await TrackingUserCRUD.get_by_telegram_id(
            session=db_session,
            telegram_id=555666777
        )
        
        assert user is not None
        assert user.telegram_id == 555666777
    
    async def test_get_by_uuid(self, db_session: AsyncSession):
        """Тест пошуку користувача за UUID."""
        # Створюємо користувача
        created_user = await TrackingUserCRUD.create_or_update(
            session=db_session,
            telegram_id=888999000,
            acquisition_source="organic"
        )
        
        uuid_to_find = created_user.user_uuid
        
        # Шукаємо за UUID
        user = await TrackingUserCRUD.get_by_uuid(
            session=db_session,
            user_uuid=uuid_to_find
        )
        
        assert user is not None
        assert user.user_uuid == uuid_to_find
        assert user.telegram_id == 888999000


@pytest.mark.asyncio
class TestTrackingClickCRUD:
    """Тести для TrackingClickCRUD."""
    
    async def test_create_click(self, db_session: AsyncSession):
        """Тест створення кліку."""
        # Спочатку створюємо користувача
        user = await TrackingUserCRUD.create_or_update(
            session=db_session,
            telegram_id=123123123,
            acquisition_source="ad_test_001"
        )
        
        # Створюємо клік
        click = await TrackingClickCRUD.create(
            session=db_session,
            user_uuid=user.user_uuid,
            source=user.acquisition_source,
            page="1",
            exchange="binance",
            ip_address="127.0.0.1",
            user_agent="Mozilla/5.0",
            ref_code="TEST123"
        )
        
        assert click is not None
        assert click.user_uuid == user.user_uuid
        assert click.exchange == "binance"
        assert click.page == "1"
        assert click.ip_address == "127.0.0.1"
    
    async def test_batch_create_clicks(self, db_session: AsyncSession):
        """Тест batch insert кліків."""
        # Створюємо користувачів
        user1 = await TrackingUserCRUD.create_or_update(
            session=db_session,
            telegram_id=111111,
            acquisition_source="organic"
        )
        
        user2 = await TrackingUserCRUD.create_or_update(
            session=db_session,
            telegram_id=222222,
            acquisition_source="ad_xcom_001"
        )
        
        # Batch insert
        clicks_data = [
            {
                'user_uuid': user1.user_uuid,
                'source': user1.acquisition_source,
                'page': '1',
                'exchange': 'binance'
            },
            {
                'user_uuid': user2.user_uuid,
                'source': user2.acquisition_source,
                'page': '2',
                'exchange': 'bybit'
            }
        ]
        
        count = await TrackingClickCRUD.batch_create(
            session=db_session,
            clicks_data=clicks_data
        )
        
        assert count == 2
    
    async def test_get_by_user(self, db_session: AsyncSession):
        """Тест отримання кліків користувача."""
        # Створюємо користувача та кліки
        user = await TrackingUserCRUD.create_or_update(
            session=db_session,
            telegram_id=333333,
            acquisition_source="organic"
        )
        
        await TrackingClickCRUD.create(
            session=db_session,
            user_uuid=user.user_uuid,
            source=user.acquisition_source,
            page="1",
            exchange="binance"
        )
        
        await TrackingClickCRUD.create(
            session=db_session,
            user_uuid=user.user_uuid,
            source=user.acquisition_source,
            page="2",
            exchange="bybit"
        )
        
        # Отримуємо кліки
        clicks = await TrackingClickCRUD.get_by_user(
            session=db_session,
            user_uuid=user.user_uuid
        )
        
        assert len(clicks) == 2


@pytest.mark.asyncio
class TestTrackingCampaignCRUD:
    """Тести для TrackingCampaignCRUD."""
    
    async def test_create_campaign(self, db_session: AsyncSession):
        """Тест створення кампанії."""
        campaign = await TrackingCampaignCRUD.create_or_update(
            session=db_session,
            campaign_id="nov2025_123",
            platform="xcom",
            description="Test campaign"
        )
        
        assert campaign is not None
        assert campaign.campaign_id == "nov2025_123"
        assert campaign.platform == "xcom"
        assert campaign.total_users == 0
        assert campaign.total_clicks == 0
    
    async def test_upsert_campaign(self, db_session: AsyncSession):
        """Тест UPSERT кампанії."""
        # Створюємо кампанію
        campaign1 = await TrackingCampaignCRUD.create_or_update(
            session=db_session,
            campaign_id="test_campaign",
            platform="xcom",
            description="Original description"
        )
        
        # Оновлюємо
        campaign2 = await TrackingCampaignCRUD.create_or_update(
            session=db_session,
            campaign_id="test_campaign",
            platform="telegram_ads",  # Змінюємо платформу
            description="Updated description"
        )
        
        assert campaign1.id == campaign2.id  # Той самий запис
        assert campaign2.platform == "telegram_ads"  # Оновлено
        assert campaign2.description == "Updated description"
    
    async def test_increment_users(self, db_session: AsyncSession):
        """Тест інкременту користувачів."""
        campaign = await TrackingCampaignCRUD.create_or_update(
            session=db_session,
            campaign_id="increment_test",
            platform="xcom"
        )
        
        assert campaign.total_users == 0
        
        # Інкремент
        await TrackingCampaignCRUD.increment_users(
            session=db_session,
            campaign_id="increment_test"
        )
        
        # Перевіряємо
        updated_campaign = await TrackingCampaignCRUD.get_by_id(
            session=db_session,
            campaign_id="increment_test"
        )
        
        assert updated_campaign.total_users == 1
    
    async def test_get_all_active(self, db_session: AsyncSession):
        """Тест отримання активних кампаній."""
        # Створюємо активну кампанію (без end_date)
        await TrackingCampaignCRUD.create_or_update(
            session=db_session,
            campaign_id="active_campaign",
            platform="xcom",
            end_date=None
        )
        
        # Отримуємо всі активні
        active_campaigns = await TrackingCampaignCRUD.get_all_active(
            session=db_session
        )
        
        assert len(active_campaigns) >= 1
        assert any(c.campaign_id == "active_campaign" for c in active_campaigns)


@pytest.mark.asyncio
class TestTrackingLogCRUD:
    """Тести для TrackingLogCRUD."""
    
    async def test_create_log(self, db_session: AsyncSession):
        """Тест створення лога."""
        log = await TrackingLogCRUD.create(
            session=db_session,
            event_type="error",
            message="Test error message",
            context={"test": "data"}
        )
        
        assert log is not None
        assert log.event_type == "error"
        assert log.message == "Test error message"
        assert log.context == {"test": "data"}
    
    async def test_get_recent_logs(self, db_session: AsyncSession):
        """Тест отримання останніх логів."""
        # Створюємо кілька логів
        await TrackingLogCRUD.create(
            session=db_session,
            event_type="info",
            message="Info message 1"
        )
        
        await TrackingLogCRUD.create(
            session=db_session,
            event_type="warning",
            message="Warning message"
        )
        
        # Отримуємо всі логи
        all_logs = await TrackingLogCRUD.get_recent(
            session=db_session,
            limit=10
        )
        
        assert len(all_logs) >= 2
        
        # Отримуємо тільки warnings
        warning_logs = await TrackingLogCRUD.get_recent(
            session=db_session,
            event_type="warning",
            limit=10
        )
        
        assert len(warning_logs) >= 1
        assert all(log.event_type == "warning" for log in warning_logs)

