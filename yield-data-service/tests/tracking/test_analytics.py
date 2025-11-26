"""
Unit тести для TrackingAnalytics.

Тестує:
- CTR обчислення
- Conversion rate
- Popular exchanges
- User journey
"""

import pytest
from datetime import datetime, UTC
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.tracking_crud import TrackingUserCRUD, TrackingClickCRUD, TrackingCampaignCRUD
from app.services.tracking.analytics import tracking_analytics


@pytest.mark.asyncio
class TestTrackingAnalytics:
    """Тести для аналітики."""
    
    async def test_ctr_calculation(self, db_session: AsyncSession):
        """Тест обчислення CTR."""
        # Створюємо тестові дані
        user1 = await TrackingUserCRUD.create_or_update(
            session=db_session,
            telegram_id=11111,
            acquisition_source="test_ctr_001"
        )
        
        user2 = await TrackingUserCRUD.create_or_update(
            session=db_session,
            telegram_id=22222,
            acquisition_source="test_ctr_001"
        )
        
        # user1: 3 кліки на page=1
        for _ in range(3):
            await TrackingClickCRUD.create(
                session=db_session,
                user_uuid=user1.user_uuid,
                source=user1.acquisition_source,
                page="1",
                exchange="binance"
            )
        
        # user2: 1 клік на page=1
        await TrackingClickCRUD.create(
            session=db_session,
            user_uuid=user2.user_uuid,
            source=user2.acquisition_source,
            page="1",
            exchange="bybit"
        )
        
        # Обчислюємо CTR
        ctr_data = await tracking_analytics.get_ctr_by_pages(
            session=db_session
        )
        
        # Шукаємо page=1
        page1_ctr = next((p for p in ctr_data if p['page'] == '1'), None)
        
        assert page1_ctr is not None
        assert page1_ctr['total_clicks'] >= 4
        assert page1_ctr['unique_users'] >= 2
        # CTR = 4 clicks / 2 users = 2.0
        assert page1_ctr['ctr'] >= 2.0
    
    async def test_conversion_rate(self, db_session: AsyncSession):
        """Тест обчислення conversion rate."""
        # Створюємо 3 користувачі
        user1 = await TrackingUserCRUD.create_or_update(
            session=db_session,
            telegram_id=11001,
            acquisition_source="test_conv_001"
        )
        
        await TrackingUserCRUD.create_or_update(
            session=db_session,
            telegram_id=11002,
            acquisition_source="test_conv_001"
        )
        
        await TrackingUserCRUD.create_or_update(
            session=db_session,
            telegram_id=11003,
            acquisition_source="test_conv_001"
        )
        
        # Тільки user1 клікає
        await TrackingClickCRUD.create(
            session=db_session,
            user_uuid=user1.user_uuid,
            source=user1.acquisition_source,
            page="1",
            exchange="binance"
        )
        
        # Обчислюємо conversion
        conversion_data = await tracking_analytics.get_conversion_rate(
            session=db_session,
            source_pattern="test_conv_%"
        )
        
        # 3 користувачі, 1 з кліком = 33.33% conversion
        assert conversion_data['total_users'] >= 3
        assert conversion_data['users_with_clicks'] >= 1
    
    async def test_popular_exchanges(self, db_session: AsyncSession):
        """Тест аналізу популярних бірж."""
        # Створюємо користувача
        user = await TrackingUserCRUD.create_or_update(
            session=db_session,
            telegram_id=99001,
            acquisition_source="test_popular"
        )
        
        # Створюємо кліки на різні біржі
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
            page="1",
            exchange="binance"
        )
        
        await TrackingClickCRUD.create(
            session=db_session,
            user_uuid=user.user_uuid,
            source=user.acquisition_source,
            page="1",
            exchange="bybit"
        )
        
        # Отримуємо популярні біржі
        popular = await tracking_analytics.get_popular_exchanges(
            session=db_session,
            limit=10
        )
        
        assert len(popular) >= 2
        # Binance має бути першим (2 кліки)
        binance_data = next((e for e in popular if e['exchange'] == 'binance'), None)
        assert binance_data is not None
        assert binance_data['total_clicks'] >= 2
    
    async def test_user_journey(self, db_session: AsyncSession):
        """Тест user journey."""
        # Створюємо користувача
        user = await TrackingUserCRUD.create_or_update(
            session=db_session,
            telegram_id=88001,
            acquisition_source="ad_journey_test"
        )
        
        # Створюємо кліки в хронологічному порядку
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
        
        # Отримуємо journey
        journey = await tracking_analytics.get_user_journey(
            session=db_session,
            user_uuid=user.user_uuid
        )
        
        assert journey is not None
        assert journey['user_uuid'] == user.user_uuid
        assert journey['total_clicks'] == 2
        assert 'binance' in journey['exchanges_clicked']
        assert 'bybit' in journey['exchanges_clicked']
        assert journey['time_to_first_click_seconds'] is not None


@pytest.mark.asyncio
class TestCampaignPerformance:
    """Тести для аналізу ефективності кампаній."""
    
    async def test_campaign_performance(self, db_session: AsyncSession):
        """Тест аналізу ефективності кампанії."""
        # Створюємо кампанію
        campaign = await TrackingCampaignCRUD.create_or_update(
            session=db_session,
            campaign_id="perf_test_001",
            platform="xcom",
            description="Performance test campaign"
        )
        
        # Створюємо користувачів та кліки
        user1 = await TrackingUserCRUD.create_or_update(
            session=db_session,
            telegram_id=77001,
            acquisition_source="ad_xcom_perf_test_001"
        )
        
        await TrackingClickCRUD.create(
            session=db_session,
            user_uuid=user1.user_uuid,
            source=user1.acquisition_source,
            page="1",
            exchange="binance"
        )
        
        # Інкремент метрик
        await TrackingCampaignCRUD.increment_users(
            session=db_session,
            campaign_id="perf_test_001"
        )
        
        await TrackingCampaignCRUD.increment_clicks(
            session=db_session,
            campaign_id="perf_test_001"
        )
        
        # Аналіз
        performance = await tracking_analytics.get_campaign_performance(
            session=db_session,
            campaign_id="perf_test_001"
        )
        
        assert len(performance) == 1
        assert performance[0]['campaign_id'] == "perf_test_001"
        assert performance[0]['total_users'] >= 1
        assert performance[0]['total_clicks'] >= 1

