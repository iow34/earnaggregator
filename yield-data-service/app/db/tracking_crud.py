"""
CRUD операції для системи трекінгу.

Забезпечує операції Create, Read, Update, Delete для таблиць трекінгу
з підтримкою batch insert, upsert та race condition handling.
"""

import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, UTC
from sqlalchemy import select, update, delete, func, and_, or_, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.db.models import (
    TrackingUser, TrackingClick, TrackingCampaign,
    TrackingSession, TrackingLog, SimpleClick
)
from app.utils.logger import logger


class TrackingUserCRUD:
    """CRUD операції для користувачів трекінгу."""
    
    @staticmethod
    def generate_uuid() -> str:
        """Генерує UUID для користувача."""
        return str(uuid.uuid4())
    
    @staticmethod
    async def get_by_telegram_id(
        session: AsyncSession,
        telegram_id: int
    ) -> Optional[TrackingUser]:
        """
        Отримати користувача за Telegram ID.
        
        Args:
            session: Сесія БД
            telegram_id: Telegram ID користувача
            
        Returns:
            TrackingUser або None
        """
        try:
            result = await session.execute(
                select(TrackingUser).where(TrackingUser.telegram_id == telegram_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"❌ Помилка отримання користувача {telegram_id}: {e}")
            return None
    
    @staticmethod
    async def get_by_uuid(
        session: AsyncSession,
        user_uuid: str
    ) -> Optional[TrackingUser]:
        """
        Отримати користувача за UUID.
        
        Args:
            session: Сесія БД
            user_uuid: UUID користувача
            
        Returns:
            TrackingUser або None
        """
        try:
            result = await session.execute(
                select(TrackingUser).where(TrackingUser.user_uuid == user_uuid)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"❌ Помилка отримання користувача за UUID {user_uuid}: {e}")
            return None
    
    @staticmethod
    async def create_or_update(
        session: AsyncSession,
        telegram_id: int,
        acquisition_source: str
    ) -> TrackingUser:
        """
        Створити або оновити користувача (UPSERT).
        
        Використовує ON CONFLICT для захисту від race conditions.
        Якщо користувач існує і має organic source, оновлює на рекламний.
        
        Args:
            session: Сесія БД
            telegram_id: Telegram ID користувача
            acquisition_source: Джерело входу
            
        Returns:
            TrackingUser
        """
        try:
            # Генеруємо UUID
            user_uuid = TrackingUserCRUD.generate_uuid()
            now = datetime.now(UTC).replace(tzinfo=None)
            
            # Використовуємо PostgreSQL UPSERT (INSERT ... ON CONFLICT)
            stmt = insert(TrackingUser).values(
                telegram_id=telegram_id,
                user_uuid=user_uuid,
                acquisition_source=acquisition_source,
                joined_at=now,
                last_activity=now
            )
            
            # ON CONFLICT: якщо користувач існує
            # - Оновлюємо source тільки якщо поточний = organic і новий не organic
            # - Завжди оновлюємо last_activity
            stmt = stmt.on_conflict_do_update(
                index_elements=['telegram_id'],
                set_={
                    'acquisition_source': case(
                        (
                            and_(
                                TrackingUser.acquisition_source == 'organic',
                                acquisition_source != 'organic'
                            ),
                            acquisition_source
                        ),
                        else_=TrackingUser.acquisition_source
                    ),
                    'last_activity': now
                }
            ).returning(TrackingUser)
            
            result = await session.execute(stmt)
            user = result.scalar_one()
            await session.commit()
            
            logger.info(f"✅ Користувач створено/оновлено: telegram_id={telegram_id}, uuid={user.user_uuid}, source={user.acquisition_source}")
            return user
            
        except Exception as e:
            logger.error(f"❌ Помилка створення/оновлення користувача {telegram_id}: {e}")
            try:
                await session.rollback()
            except:
                pass
            raise
    
    @staticmethod
    async def update_last_activity(
        session: AsyncSession,
        user_uuid: str
    ) -> bool:
        """
        Оновити час останньої активності користувача.
        
        Args:
            session: Сесія БД
            user_uuid: UUID користувача
            
        Returns:
            True якщо успішно
        """
        try:
            stmt = update(TrackingUser).where(
                TrackingUser.user_uuid == user_uuid
            ).values(
                last_activity=datetime.now(UTC).replace(tzinfo=None)
            )
            await session.execute(stmt)
            await session.commit()
            return True
        except Exception as e:
            logger.error(f"❌ Помилка оновлення активності {user_uuid}: {e}")
            try:
                await session.rollback()
            except:
                pass
            return False


class TrackingClickCRUD:
    """CRUD операції для кліків."""
    
    @staticmethod
    async def create(
        session: AsyncSession,
        user_uuid: str,
        source: str,
        page: str,
        exchange: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        ref_code: Optional[str] = None
    ) -> TrackingClick:
        """
        Створити запис кліку.
        
        Args:
            session: Сесія БД
            user_uuid: UUID користувача
            source: Джерело входу
            page: Сторінка бота
            exchange: Назва біржі
            ip_address: IP адреса
            user_agent: User Agent
            ref_code: Реферальний код
            
        Returns:
            TrackingClick
        """
        try:
            click = TrackingClick(
                user_uuid=user_uuid,
                source=source,
                page=page,
                exchange=exchange.lower(),
                timestamp=datetime.now(UTC).replace(tzinfo=None),
                ip_address=ip_address,
                user_agent=user_agent,
                ref_code=ref_code
            )
            
            session.add(click)
            await session.commit()
            await session.refresh(click)
            
            logger.info(f"✅ Клік записано: uuid={user_uuid}, exchange={exchange}, page={page}")
            return click
            
        except Exception as e:
            logger.error(f"❌ Помилка створення кліку: {e}")
            try:
                await session.rollback()
            except:
                pass
            raise
    
    @staticmethod
    async def batch_create(
        session: AsyncSession,
        clicks_data: List[Dict[str, Any]]
    ) -> int:
        """
        Batch insert кліків.
        
        Args:
            session: Сесія БД
            clicks_data: Список словників з даними кліків
            
        Returns:
            Кількість створених записів
        """
        try:
            if not clicks_data:
                return 0
            
            # Підготовка даних
            clicks = []
            now = datetime.now(UTC).replace(tzinfo=None)
            
            for data in clicks_data:
                click = TrackingClick(
                    user_uuid=data['user_uuid'],
                    source=data['source'],
                    page=data['page'],
                    exchange=data['exchange'].lower(),
                    timestamp=data.get('timestamp', now),
                    ip_address=data.get('ip_address'),
                    user_agent=data.get('user_agent'),
                    ref_code=data.get('ref_code')
                )
                clicks.append(click)
            
            session.add_all(clicks)
            await session.commit()
            
            logger.info(f"✅ Batch insert: {len(clicks)} кліків створено")
            return len(clicks)
            
        except Exception as e:
            logger.error(f"❌ Помилка batch insert кліків: {e}")
            try:
                await session.rollback()
            except:
                pass
            raise
    
    @staticmethod
    async def get_by_user(
        session: AsyncSession,
        user_uuid: str,
        limit: int = 100
    ) -> List[TrackingClick]:
        """
        Отримати кліки користувача.
        
        Args:
            session: Сесія БД
            user_uuid: UUID користувача
            limit: Максимальна кількість записів
            
        Returns:
            Список TrackingClick
        """
        try:
            result = await session.execute(
                select(TrackingClick)
                .where(TrackingClick.user_uuid == user_uuid)
                .order_by(TrackingClick.timestamp.desc())
                .limit(limit)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"❌ Помилка отримання кліків користувача {user_uuid}: {e}")
            return []
    
    @staticmethod
    async def get_by_campaign(
        session: AsyncSession,
        source_pattern: str,
        limit: int = 1000
    ) -> List[TrackingClick]:
        """
        Отримати кліки по кампанії.
        
        Args:
            session: Сесія БД
            source_pattern: Шаблон джерела (наприклад, 'ad_xcom_%')
            limit: Максимальна кількість записів
            
        Returns:
            Список TrackingClick
        """
        try:
            result = await session.execute(
                select(TrackingClick)
                .where(TrackingClick.source.like(source_pattern))
                .order_by(TrackingClick.timestamp.desc())
                .limit(limit)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"❌ Помилка отримання кліків по кампанії {source_pattern}: {e}")
            return []


class TrackingCampaignCRUD:
    """CRUD операції для кампаній."""
    
    @staticmethod
    async def create_or_update(
        session: AsyncSession,
        campaign_id: str,
        platform: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        description: Optional[str] = None
    ) -> TrackingCampaign:
        """
        Створити або оновити кампанію (UPSERT).
        
        Args:
            session: Сесія БД
            campaign_id: ID кампанії
            platform: Платформа
            start_date: Дата початку
            end_date: Дата закінчення
            description: Опис
            
        Returns:
            TrackingCampaign
        """
        try:
            now = datetime.now(UTC).replace(tzinfo=None)
            
            stmt = insert(TrackingCampaign).values(
                campaign_id=campaign_id,
                platform=platform,
                start_date=start_date or now,
                end_date=end_date,
                description=description or f"Auto-created campaign {campaign_id}",
                total_users=0,
                total_clicks=0,
                created_at=now,
                updated_at=now
            )
            
            stmt = stmt.on_conflict_do_update(
                index_elements=['campaign_id'],
                set_={
                    'platform': platform,
                    'end_date': end_date,
                    'description': description or TrackingCampaign.description,
                    'updated_at': now
                }
            ).returning(TrackingCampaign)
            
            result = await session.execute(stmt)
            campaign = result.scalar_one()
            await session.commit()
            
            logger.info(f"✅ Кампанія створена/оновлена: {campaign_id}, platform={platform}")
            return campaign
            
        except Exception as e:
            logger.error(f"❌ Помилка створення/оновлення кампанії {campaign_id}: {e}")
            try:
                await session.rollback()
            except:
                pass
            raise
    
    @staticmethod
    async def get_by_id(
        session: AsyncSession,
        campaign_id: str
    ) -> Optional[TrackingCampaign]:
        """Отримати кампанію за ID."""
        try:
            result = await session.execute(
                select(TrackingCampaign).where(TrackingCampaign.campaign_id == campaign_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"❌ Помилка отримання кампанії {campaign_id}: {e}")
            return None
    
    @staticmethod
    async def increment_users(
        session: AsyncSession,
        campaign_id: str
    ) -> bool:
        """Збільшити лічильник користувачів кампанії."""
        try:
            stmt = update(TrackingCampaign).where(
                TrackingCampaign.campaign_id == campaign_id
            ).values(
                total_users=TrackingCampaign.total_users + 1
            )
            await session.execute(stmt)
            await session.commit()
            return True
        except Exception as e:
            logger.error(f"❌ Помилка інкременту користувачів {campaign_id}: {e}")
            await session.rollback()
            return False
    
    @staticmethod
    async def increment_clicks(
        session: AsyncSession,
        campaign_id: str
    ) -> bool:
        """Збільшити лічильник кліків кампанії."""
        try:
            stmt = update(TrackingCampaign).where(
                TrackingCampaign.campaign_id == campaign_id
            ).values(
                total_clicks=TrackingCampaign.total_clicks + 1
            )
            await session.execute(stmt)
            await session.commit()
            return True
        except Exception as e:
            logger.error(f"❌ Помилка інкременту кліків {campaign_id}: {e}")
            await session.rollback()
            return False
    
    @staticmethod
    async def get_all_active(
        session: AsyncSession
    ) -> List[TrackingCampaign]:
        """Отримати всі активні кампанії (без end_date або end_date > now)."""
        try:
            now = datetime.now(UTC).replace(tzinfo=None)
            result = await session.execute(
                select(TrackingCampaign).where(
                    or_(
                        TrackingCampaign.end_date.is_(None),
                        TrackingCampaign.end_date > now
                    )
                ).order_by(TrackingCampaign.start_date.desc())
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"❌ Помилка отримання активних кампаній: {e}")
            return []


class TrackingSessionCRUD:
    """CRUD операції для сесій."""
    
    @staticmethod
    def generate_session_id() -> str:
        """Генерує UUID для сесії."""
        return str(uuid.uuid4())
    
    @staticmethod
    async def create(
        session: AsyncSession,
        user_uuid: str,
        source: str
    ) -> TrackingSession:
        """
        Створити нову сесію.
        
        Args:
            session: Сесія БД
            user_uuid: UUID користувача
            source: Джерело входу
            
        Returns:
            TrackingSession
        """
        try:
            session_id = TrackingSessionCRUD.generate_session_id()
            now = datetime.now(UTC).replace(tzinfo=None)
            
            tracking_session = TrackingSession(
                user_uuid=user_uuid,
                session_id=session_id,
                source=source,
                session_start=now,
                total_clicks=0,
                total_time=0
            )
            
            session.add(tracking_session)
            await session.commit()
            await session.refresh(tracking_session)
            
            logger.info(f"✅ Сесія створена: session_id={session_id}, uuid={user_uuid}")
            return tracking_session
            
        except Exception as e:
            logger.error(f"❌ Помилка створення сесії: {e}")
            await session.rollback()
            raise
    
    @staticmethod
    async def end_session(
        session: AsyncSession,
        session_id: str
    ) -> bool:
        """Завершити сесію."""
        try:
            # Отримуємо сесію
            result = await session.execute(
                select(TrackingSession).where(TrackingSession.session_id == session_id)
            )
            tracking_session = result.scalar_one_or_none()
            
            if not tracking_session:
                return False
            
            now = datetime.now(UTC).replace(tzinfo=None)
            duration = int((now - tracking_session.session_start).total_seconds())
            
            stmt = update(TrackingSession).where(
                TrackingSession.session_id == session_id
            ).values(
                session_end=now,
                total_time=duration
            )
            
            await session.execute(stmt)
            await session.commit()
            return True
            
        except Exception as e:
            logger.error(f"❌ Помилка завершення сесії {session_id}: {e}")
            await session.rollback()
            return False
    
    @staticmethod
    async def increment_clicks(
        session: AsyncSession,
        session_id: str
    ) -> bool:
        """Збільшити лічильник кліків сесії."""
        try:
            stmt = update(TrackingSession).where(
                TrackingSession.session_id == session_id
            ).values(
                total_clicks=TrackingSession.total_clicks + 1
            )
            await session.execute(stmt)
            await session.commit()
            return True
        except Exception as e:
            logger.error(f"❌ Помилка інкременту кліків сесії {session_id}: {e}")
            await session.rollback()
            return False


class TrackingLogCRUD:
    """CRUD операції для логів."""
    
    @staticmethod
    async def create(
        session: AsyncSession,
        event_type: str,
        message: str,
        user_uuid: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> TrackingLog:
        """
        Створити лог запис.
        
        Args:
            session: Сесія БД
            event_type: Тип події (error, warning, info)
            message: Текст повідомлення
            user_uuid: UUID користувача
            context: Додатковий контекст
            
        Returns:
            TrackingLog
        """
        try:
            log = TrackingLog(
                event_type=event_type,
                message=message,
                user_uuid=user_uuid,
                context=context,
                timestamp=datetime.now(UTC).replace(tzinfo=None)
            )
            
            session.add(log)
            await session.commit()
            await session.refresh(log)
            
            return log
            
        except Exception as e:
            logger.error(f"❌ Помилка створення лога: {e}")
            await session.rollback()
            raise
    
    @staticmethod
    async def get_recent(
        session: AsyncSession,
        event_type: Optional[str] = None,
        limit: int = 100
    ) -> List[TrackingLog]:
        """
        Отримати останні логи.
        
        Args:
            session: Сесія БД
            event_type: Фільтр по типу події
            limit: Максимальна кількість записів
            
        Returns:
            Список TrackingLog
        """
        try:
            query = select(TrackingLog)
            
            if event_type:
                query = query.where(TrackingLog.event_type == event_type)
            
            query = query.order_by(TrackingLog.timestamp.desc()).limit(limit)
            
            result = await session.execute(query)
            return list(result.scalars().all())
            
        except Exception as e:
            logger.error(f"❌ Помилка отримання логів: {e}")
            return []

