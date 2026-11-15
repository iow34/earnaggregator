from typing import Optional
from datetime import datetime, UTC
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.db.models import SimpleClick
from app.utils.logger import logger


class SimpleClickCRUD:
    @staticmethod
    async def create(
        session: AsyncSession,
        telegram_id: int,
        exchange: str,
        page: str,
        source: str = "organic",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        ref_code: Optional[str] = None,
    ) -> SimpleClick:
        try:
            click = SimpleClick(
                telegram_id=telegram_id,
                exchange=exchange.lower(),
                page=page,
                source=source,
                timestamp=datetime.now(UTC).replace(tzinfo=None),
                ip_address=ip_address,
                user_agent=user_agent,
                ref_code=ref_code,
            )

            session.add(click)
            await session.commit()
            await session.refresh(click)

            logger.info(
                f"✅ Простий клік записано: telegram_id={telegram_id}, "
                f"exchange={exchange}, page={page}"
            )
            return click

        except Exception as e:
            logger.error(f"❌ Помилка запису простого кліку: {e}", exc_info=True)
            try:
                await session.rollback()
            except:
                pass
            raise

    @staticmethod
    async def get_by_telegram_id(
        session: AsyncSession, telegram_id: int, limit: int = 100
    ) -> list[SimpleClick]:
        try:
            result = await session.execute(
                select(SimpleClick)
                .where(SimpleClick.telegram_id == telegram_id)
                .order_by(desc(SimpleClick.timestamp))
                .limit(limit)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"❌ Помилка отримання кліків {telegram_id}: {e}")
            return []

    @staticmethod
    async def get_stats_by_exchange(session: AsyncSession, exchange: Optional[str] = None) -> dict:
        try:
            query = select(
                SimpleClick.exchange,
                func.count(SimpleClick.id).label("total_clicks"),
                func.count(func.distinct(SimpleClick.telegram_id)).label("unique_users"),
            ).group_by(SimpleClick.exchange)

            if exchange:
                query = query.where(SimpleClick.exchange == exchange.lower())

            result = await session.execute(query)
            rows = result.all()

            return {
                row.exchange: {"total_clicks": row.total_clicks, "unique_users": row.unique_users}
                for row in rows
            }
        except Exception as e:
            logger.error(f"❌ Помилка отримання статистики: {e}")
            return {}
