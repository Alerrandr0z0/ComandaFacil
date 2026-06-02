from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

from app.analytics.domain.enums import AnalyticsPeriod
from app.analytics.domain.value_objects import (
    DashboardData,
    DateRange,
    KitchenPerformance,
    OrderInsights,
    SalesReportData,
)


class MongoAnalyticsRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:  # type: ignore[type-arg]
        self._db = db

    async def get_dashboard(
        self,
        tenant_id: str,
        period: AnalyticsPeriod = AnalyticsPeriod.DAY,  # noqa: ARG002
        date_range: DateRange | None = None,  # noqa: ARG002
    ) -> DashboardData:
        orders_coll = self._db["orders_read"]
        stock_coll = self._db["stock_read"]
        kitchen_coll = self._db["kitchen_read"]

        pipe: list[dict[str, Any]] = [
            {
                "$match": {
                    "tenant_id": tenant_id,
                    "created_at": {
                        "$gte": datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
                    },
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_sales": {"$sum": "$total"},
                    "orders_count": {"$sum": 1},
                    "avg_ticket": {"$avg": "$total"},
                }
            },
        ]
        order_stats = await orders_coll.aggregate(pipe).to_list(None)

        low_stock = await stock_coll.count_documents({"tenant_id": tenant_id, "is_low_stock": True})

        prep_pipe: list[dict[str, Any]] = [
            {"$match": {"tenant_id": tenant_id, "completed_at": {"$ne": None}}},
            {
                "$group": {
                    "_id": None,
                    "avg_prep_time": {"$avg": {"$subtract": ["$completed_at", "$started_at"]}},
                }
            },
        ]
        kitchen_stats = await kitchen_coll.aggregate(prep_pipe).to_list(None)

        total_sales = order_stats[0]["total_sales"] if order_stats else 0
        orders_count = order_stats[0]["orders_count"] if order_stats else 0
        avg_ticket = order_stats[0]["avg_ticket"] if order_stats else 0

        avg_prep = 0.0
        if kitchen_stats and kitchen_stats[0].get("avg_prep_time"):
            avg_prep = kitchen_stats[0]["avg_prep_time"] / 60000

        return DashboardData(
            total_sales=Decimal(str(total_sales)),
            orders_count=orders_count,
            average_ticket=Decimal(str(avg_ticket)),
            low_stock_items=low_stock,
            average_prep_time_minutes=avg_prep,
        )

    async def get_sales_report(
        self,
        tenant_id: str,
        period: AnalyticsPeriod = AnalyticsPeriod.DAY,
        date_range: DateRange | None = None,
    ) -> SalesReportData:
        orders_coll = self._db["orders_read"]

        match: dict[str, Any] = {"tenant_id": tenant_id}
        if date_range:
            match["created_at"] = {"$gte": date_range.start, "$lte": date_range.end}

        pipe: list[dict[str, Any]] = [
            {"$match": match},
            {
                "$group": {
                    "_id": None,
                    "total_sales": {"$sum": "$total"},
                    "total_orders": {"$sum": 1},
                    "avg_ticket": {"$avg": "$total"},
                }
            },
        ]
        stats = await orders_coll.aggregate(pipe).to_list(None)

        cat_pipe: list[dict[str, Any]] = [
            {"$match": match},
            {"$unwind": "$items"},
            {
                "$group": {
                    "_id": "$items.category",
                    "total": {"$sum": "$items.price"},
                }
            },
        ]
        by_cat = await orders_coll.aggregate(cat_pipe).to_list(None)

        total_sales = stats[0]["total_sales"] if stats else 0
        total_orders = stats[0]["total_orders"] if stats else 0
        avg_ticket = stats[0]["avg_ticket"] if stats else 0

        return SalesReportData(
            period=period,
            total_sales=Decimal(str(total_sales)),
            total_orders=total_orders,
            average_ticket=Decimal(str(avg_ticket)),
            by_category={c["_id"]: Decimal(str(c["total"])) for c in by_cat},
        )

    async def get_order_insights(
        self,
        tenant_id: str,
        period: AnalyticsPeriod = AnalyticsPeriod.DAY,
        date_range: DateRange | None = None,
    ) -> OrderInsights:
        orders_coll = self._db["orders_read"]

        match: dict[str, Any] = {"tenant_id": tenant_id}
        if date_range:
            match["created_at"] = {"$gte": date_range.start, "$lte": date_range.end}

        pipe: list[dict[str, Any]] = [
            {"$match": match},
            {
                "$group": {
                    "_id": None,
                    "total_orders": {"$sum": 1},
                    "avg_items": {"$avg": {"$size": {"$ifNull": ["$items", []]}}},
                    "peak_hour": {"$max": {"$hour": "$created_at"}},
                }
            },
        ]
        stats = await orders_coll.aggregate(pipe).to_list(None)

        total_orders = stats[0]["total_orders"] if stats else 0
        avg_items = float(stats[0]["avg_items"]) if stats else 0.0
        peak_hour = stats[0]["peak_hour"] if stats else 0

        return OrderInsights(
            period=period,
            total_orders=total_orders,
            average_items_per_order=avg_items,
            peak_hour=peak_hour,
        )

    async def get_kitchen_performance(
        self,
        tenant_id: str,
        period: AnalyticsPeriod = AnalyticsPeriod.DAY,
        date_range: DateRange | None = None,
    ) -> KitchenPerformance:
        kitchen_coll = self._db["kitchen_read"]

        match: dict[str, Any] = {"tenant_id": tenant_id}
        if date_range:
            match["created_at"] = {"$gte": date_range.start, "$lte": date_range.end}

        pipe: list[dict[str, Any]] = [
            {"$match": match},
            {
                "$group": {
                    "_id": None,
                    "avg_prep_time": {"$avg": {"$subtract": ["$completed_at", "$started_at"]}},
                    "total_prepared": {"$sum": 1},
                    "completed": {"$sum": {"$cond": [{"$eq": ["$state", "DONE"]}, 1, 0]}},
                }
            },
        ]
        stats = await kitchen_coll.aggregate(pipe).to_list(None)

        total_prepared = stats[0]["total_prepared"] if stats else 0
        completed = stats[0]["completed"] if stats else 0
        avg_prep_ms = stats[0]["avg_prep_time"] if stats else 0
        completion_rate = completed / total_prepared if total_prepared > 0 else 0.0

        return KitchenPerformance(
            period=period,
            average_prep_time_minutes=avg_prep_ms / 60000 if avg_prep_ms else 0.0,
            items_prepared=total_prepared,
            completion_rate=completion_rate,
        )
