from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, UTC
from sqlalchemy import select, func, and_, or_, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    TrackingUser,
    TrackingClick,
    TrackingCampaign,
    TrackingSession,
    TrackingLog,
)
from app.utils.logger import logger


class TrackingAnalytics:
    @staticmethod
    async def get_ctr_by_pages(
        session: AsyncSession,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        try:
            clicks_query = select(
                TrackingClick.page,
                func.count(TrackingClick.id).label("total_clicks"),
                func.count(func.distinct(TrackingClick.user_uuid)).label("unique_users"),
            ).group_by(TrackingClick.page)

            if start_date:
                clicks_query = clicks_query.where(TrackingClick.timestamp >= start_date)
            if end_date:
                clicks_query = clicks_query.where(TrackingClick.timestamp <= end_date)

            result = await session.execute(clicks_query)
            rows = result.all()

            ctr_data = []
            for row in rows:
                page = row.page
                total_clicks = row.total_clicks
                unique_users = row.unique_users

                # CTR = clicks per user
                ctr = (total_clicks / unique_users) if unique_users > 0 else 0

                ctr_data.append(
                    {
                        "page": page,
                        "total_clicks": total_clicks,
                        "unique_users": unique_users,
                        "ctr": round(ctr, 2),
                        "avg_clicks_per_user": round(ctr, 2),
                    }
                )

            return ctr_data

        except Exception as e:
            logger.error(f"❌ Помилка обчислення CTR: {e}")
            return []

    @staticmethod
    async def get_conversion_rate(
        session: AsyncSession, source_pattern: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            users_query = select(func.count(TrackingUser.id))

            if source_pattern:
                users_query = users_query.where(
                    TrackingUser.acquisition_source.like(source_pattern)
                )

            total_users_result = await session.execute(users_query)
            total_users = total_users_result.scalar() or 0

            users_with_clicks_query = select(func.count(func.distinct(TrackingClick.user_uuid)))

            if source_pattern:
                users_with_clicks_query = users_with_clicks_query.where(
                    TrackingClick.source.like(source_pattern)
                )

            users_with_clicks_result = await session.execute(users_with_clicks_query)
            users_with_clicks = users_with_clicks_result.scalar() or 0

            conversion_rate = (users_with_clicks / total_users * 100) if total_users > 0 else 0

            return {
                "total_users": total_users,
                "users_with_clicks": users_with_clicks,
                "conversion_rate": round(conversion_rate, 2),
                "source_pattern": source_pattern or "all",
            }

        except Exception as e:
            logger.error(f"❌ Помилка обчислення conversion rate: {e}")
            return {"total_users": 0, "users_with_clicks": 0, "conversion_rate": 0, "error": str(e)}

    @staticmethod
    async def get_popular_exchanges(session: AsyncSession, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            query = (
                select(
                    TrackingClick.exchange,
                    func.count(TrackingClick.id).label("total_clicks"),
                    func.count(func.distinct(TrackingClick.user_uuid)).label("unique_users"),
                )
                .group_by(TrackingClick.exchange)
                .order_by(func.count(TrackingClick.id).desc())
                .limit(limit)
            )

            result = await session.execute(query)
            rows = result.all()

            return [
                {
                    "exchange": row.exchange,
                    "total_clicks": row.total_clicks,
                    "unique_users": row.unique_users,
                    "avg_clicks_per_user": round(row.total_clicks / row.unique_users, 2)
                    if row.unique_users > 0
                    else 0,
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"❌ Помилка отримання популярних бірж: {e}")
            return []

    @staticmethod
    async def get_user_journey(session: AsyncSession, user_uuid: str) -> Dict[str, Any]:
        try:
            user_query = select(TrackingUser).where(TrackingUser.user_uuid == user_uuid)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one_or_none()

            if not user:
                return {"error": "User not found"}

            clicks_query = (
                select(TrackingClick)
                .where(TrackingClick.user_uuid == user_uuid)
                .order_by(TrackingClick.timestamp.asc())
            )

            clicks_result = await session.execute(clicks_query)
            clicks = clicks_result.scalars().all()

            time_to_first_click = None
            if clicks:
                first_click = clicks[0]
                time_diff = first_click.timestamp - user.joined_at
                time_to_first_click = int(time_diff.total_seconds())

            exchanges_clicked = {}
            for click in clicks:
                exchange = click.exchange
                if exchange not in exchanges_clicked:
                    exchanges_clicked[exchange] = 0
                exchanges_clicked[exchange] += 1

            return {
                "user_uuid": user_uuid,
                "acquisition_source": user.acquisition_source,
                "joined_at": user.joined_at.isoformat(),
                "last_activity": user.last_activity.isoformat(),
                "total_clicks": len(clicks),
                "time_to_first_click_seconds": time_to_first_click,
                "exchanges_clicked": exchanges_clicked,
                "click_timeline": [
                    {"exchange": c.exchange, "page": c.page, "timestamp": c.timestamp.isoformat()}
                    for c in clicks
                ],
            }

        except Exception as e:
            logger.error(f"❌ Помилка отримання user journey: {e}")
            return {"error": str(e)}

    @staticmethod
    async def get_campaign_performance(
        session: AsyncSession, campaign_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        try:
            query = select(
                TrackingCampaign.campaign_id,
                TrackingCampaign.platform,
                TrackingCampaign.total_users,
                TrackingCampaign.total_clicks,
                TrackingCampaign.start_date,
                TrackingCampaign.end_date,
            )

            if campaign_id:
                query = query.where(TrackingCampaign.campaign_id == campaign_id)

            query = query.order_by(TrackingCampaign.total_users.desc())

            result = await session.execute(query)
            rows = result.all()

            campaigns_data = []
            for row in rows:
                conversion_rate = (
                    (row.total_clicks / row.total_users * 100) if row.total_users > 0 else 0
                )

                if row.end_date:
                    duration = (row.end_date - row.start_date).days
                    is_active = row.end_date > datetime.now(UTC).replace(tzinfo=None)
                else:
                    duration = (datetime.now(UTC).replace(tzinfo=None) - row.start_date).days
                    is_active = True

                campaigns_data.append(
                    {
                        "campaign_id": row.campaign_id,
                        "platform": row.platform,
                        "total_users": row.total_users,
                        "total_clicks": row.total_clicks,
                        "conversion_rate": round(conversion_rate, 2),
                        "avg_clicks_per_user": round(row.total_clicks / row.total_users, 2)
                        if row.total_users > 0
                        else 0,
                        "duration_days": duration,
                        "is_active": is_active,
                        "start_date": row.start_date.isoformat(),
                        "end_date": row.end_date.isoformat() if row.end_date else None,
                    }
                )

            return campaigns_data

        except Exception as e:
            logger.error(f"❌ Помилка аналізу кампаній: {e}")
            return []

    @staticmethod
    async def get_time_based_analytics(
        session: AsyncSession, period_hours: int = 24
    ) -> Dict[str, Any]:
        try:
            cutoff_time = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=period_hours)

            new_users_query = select(func.count(TrackingUser.id)).where(
                TrackingUser.joined_at >= cutoff_time
            )
            new_users_result = await session.execute(new_users_query)
            new_users = new_users_result.scalar() or 0

            clicks_query = select(func.count(TrackingClick.id)).where(
                TrackingClick.timestamp >= cutoff_time
            )
            clicks_result = await session.execute(clicks_query)
            total_clicks = clicks_result.scalar() or 0

            active_users_query = select(func.count(func.distinct(TrackingClick.user_uuid))).where(
                TrackingClick.timestamp >= cutoff_time
            )
            active_users_result = await session.execute(active_users_query)
            active_users = active_users_result.scalar() or 0

            return {
                "period_hours": period_hours,
                "start_time": cutoff_time.isoformat(),
                "end_time": datetime.now(UTC).replace(tzinfo=None).isoformat(),
                "new_users": new_users,
                "total_clicks": total_clicks,
                "active_users": active_users,
                "avg_clicks_per_active_user": round(total_clicks / active_users, 2)
                if active_users > 0
                else 0,
            }

        except Exception as e:
            logger.error(f"❌ Помилка time-based аналітики: {e}")
            return {"error": str(e)}

    @staticmethod
    async def get_source_breakdown(session: AsyncSession, limit: int = 20) -> List[Dict[str, Any]]:
        try:
            users_query = (
                select(
                    TrackingUser.acquisition_source,
                    func.count(TrackingUser.id).label("total_users"),
                )
                .group_by(TrackingUser.acquisition_source)
                .order_by(func.count(TrackingUser.id).desc())
                .limit(limit)
            )

            users_result = await session.execute(users_query)
            users_rows = users_result.all()

            source_data = []
            for row in users_rows:
                source = row.acquisition_source
                total_users = row.total_users

                clicks_query = select(func.count(TrackingClick.id)).where(
                    TrackingClick.source == source
                )
                clicks_result = await session.execute(clicks_query)
                total_clicks = clicks_result.scalar() or 0

                # Conversion rate
                conversion_rate = (total_clicks / total_users * 100) if total_users > 0 else 0

                source_data.append(
                    {
                        "source": source,
                        "total_users": total_users,
                        "total_clicks": total_clicks,
                        "conversion_rate": round(conversion_rate, 2),
                        "avg_clicks_per_user": round(total_clicks / total_users, 2)
                        if total_users > 0
                        else 0,
                    }
                )

            return source_data

        except Exception as e:
            logger.error(f"❌ Помилка source breakdown: {e}")
            return []

    @staticmethod
    async def get_hourly_distribution(session: AsyncSession, days: int = 7) -> List[Dict[str, Any]]:
        try:
            cutoff_date = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days)

            query = (
                select(
                    func.extract("hour", TrackingClick.timestamp).label("hour"),
                    func.count(TrackingClick.id).label("clicks_count"),
                )
                .where(TrackingClick.timestamp >= cutoff_date)
                .group_by(func.extract("hour", TrackingClick.timestamp))
                .order_by(func.extract("hour", TrackingClick.timestamp))
            )

            result = await session.execute(query)
            rows = result.all()

            hourly_data = [{"hour": h, "clicks": 0} for h in range(24)]

            for row in rows:
                hour = int(row.hour)
                clicks = row.clicks_count
                hourly_data[hour]["clicks"] = clicks

            return hourly_data

        except Exception as e:
            logger.error(f"❌ Помилка hourly distribution: {e}")
            return []

    @staticmethod
    async def get_page_to_exchange_flow(session: AsyncSession) -> Dict[str, Any]:
        try:
            query = (
                select(
                    TrackingClick.page,
                    TrackingClick.exchange,
                    func.count(TrackingClick.id).label("clicks"),
                )
                .group_by(TrackingClick.page, TrackingClick.exchange)
                .order_by(TrackingClick.page, func.count(TrackingClick.id).desc())
            )

            result = await session.execute(query)
            rows = result.all()

            flow_data = {}
            for row in rows:
                page = row.page
                exchange = row.exchange
                clicks = row.clicks

                if page not in flow_data:
                    flow_data[page] = {}

                flow_data[page][exchange] = clicks

            return {"flow_matrix": flow_data, "total_pages": len(flow_data)}

        except Exception as e:
            logger.error(f"❌ Помилка page-to-exchange flow: {e}")
            return {"error": str(e)}

    @staticmethod
    async def get_recent_activity(
        session: AsyncSession, hours: int = 1, limit: int = 50
    ) -> List[Dict[str, Any]]:
        try:
            cutoff_time = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=hours)

            query = (
                select(TrackingClick)
                .where(TrackingClick.timestamp >= cutoff_time)
                .order_by(TrackingClick.timestamp.desc())
                .limit(limit)
            )

            result = await session.execute(query)
            clicks = result.scalars().all()

            return [
                {
                    "user_uuid": c.user_uuid,
                    "exchange": c.exchange,
                    "page": c.page,
                    "source": c.source,
                    "timestamp": c.timestamp.isoformat(),
                    "ip_address": c.ip_address,
                }
                for c in clicks
            ]

        except Exception as e:
            logger.error(f"❌ Помилка recent activity: {e}")
            return []


tracking_analytics = TrackingAnalytics()
