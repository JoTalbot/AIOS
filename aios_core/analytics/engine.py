from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aios_core.models import MessageLog, Metric


class AnalyticsEngine:
    def __init__(self, db_session: AsyncSession = None):
        self.db = db_session

    async def get_conversion_rate(self, days: int = 7) -> dict[str, float]:
        if not self.db:
            return {"period_days": days, "created": 0, "approved": 0, "rate": 0.0}
        cutoff = datetime.now(UTC) - timedelta(days=days)
        created_q = await self.db.execute(
            select(func.count())
            .select_from(Metric)
            .where(Metric.metric_type == "draft_created", Metric.created_at > cutoff)
        )
        approved_q = await self.db.execute(
            select(func.count())
            .select_from(Metric)
            .where(Metric.metric_type == "draft_approved", Metric.created_at > cutoff)
        )
        created = created_q.scalar() or 0
        approved = approved_q.scalar() or 0
        rate = (approved / created * 100) if created > 0 else 0
        return {"period_days": days, "created": created, "approved": approved, "rate": round(rate, 2)}

    async def get_avg_response_time(self, days: int = 7) -> float:
        if not self.db:
            return 0.0
        cutoff = datetime.now(UTC) - timedelta(days=days)
        result = await self.db.execute(
            select(func.avg(MessageLog.processing_time)).where(
                MessageLog.created_at > cutoff, MessageLog.processing_time.isnot(None)
            )
        )
        return result.scalar() or 0.0

    async def get_top_platforms(self, days: int = 30) -> list[dict[str, Any]]:
        if not self.db:
            return []
        cutoff = datetime.now(UTC) - timedelta(days=days)
        result = await self.db.execute(
            select(MessageLog.platform, func.count().label("count"))
            .where(MessageLog.created_at > cutoff)
            .group_by(MessageLog.platform)
            .order_by(func.count().desc())
        )
        return [{"platform": row[0], "count": row[1]} for row in result]

    async def get_intent_distribution(self, days: int = 7) -> dict[str, int]:
        if not self.db:
            return {}
        cutoff = datetime.now(UTC) - timedelta(days=days)
        result = await self.db.execute(
            select(MessageLog.intent, func.count().label("count"))
            .where(MessageLog.created_at > cutoff, MessageLog.intent.isnot(None))
            .group_by(MessageLog.intent)
        )
        return {row[0]: row[1] for row in result}

    async def get_seasonal_patterns(self, days: int = 30) -> dict[str, int]:
        if not self.db:
            return {}
        cutoff = datetime.now(UTC) - timedelta(days=days)
        result = await self.db.execute(select(MessageLog).where(MessageLog.created_at > cutoff))
        hourly = defaultdict(int)
        for log in result.scalars():
            hourly[log.created_at.hour] += 1
        return {str(h): c for h, c in sorted(hourly.items())}

    async def get_full_report(self) -> dict[str, Any]:
        return {
            "conversion_7d": await self.get_conversion_rate(7),
            "conversion_30d": await self.get_conversion_rate(30),
            "avg_response_time_7d": round(await self.get_avg_response_time(7), 2),
            "top_platforms_30d": await self.get_top_platforms(30),
            "intent_distribution_7d": await self.get_intent_distribution(7),
            "seasonal_patterns_30d": await self.get_seasonal_patterns(30),
        }
