from __future__ import annotations

from datetime import UTC, datetime, timedelta
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

    def _resolve_date_range(
        self, period: AnalyticsPeriod, date_range: DateRange | None
    ) -> DateRange:
        if date_range:
            return date_range
        now = datetime.now(UTC)
        if period == AnalyticsPeriod.DAY:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == AnalyticsPeriod.WEEK:
            start = now - timedelta(days=7)
        else:  # MONTH
            start = now - timedelta(days=30)
        return DateRange(start=start, end=now)

    async def get_dashboard(
        self,
        tenant_id: str,
        period: AnalyticsPeriod = AnalyticsPeriod.DAY,
        date_range: DateRange | None = None,
    ) -> DashboardData:
        orders_coll = self._db["orders_read"]
        stock_coll = self._db["stock_read"]
        kitchen_coll = self._db["kitchen_read"]

        dr = self._resolve_date_range(period, date_range)

        pipe: list[dict[str, Any]] = [
            {
                "$match": {
                    "tenant_id": tenant_id,
                    "created_at": {
                        "$gte": dr.start,
                        "$lte": dr.end,
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
            {
                "$match": {
                    "tenant_id": tenant_id,
                    "completed_at": {"$ne": None},
                    "created_at": {
                        "$gte": dr.start,
                        "$lte": dr.end,
                    },
                }
            },
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

        dr = self._resolve_date_range(period, date_range)
        match: dict[str, Any] = {
            "tenant_id": tenant_id,
            "created_at": {"$gte": dr.start, "$lte": dr.end},
        }

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

        # Fetch sales trends
        trends: list[dict[str, Any]] = []
        if period == AnalyticsPeriod.DAY:
            trend_pipe = [
                {"$match": match},
                {
                    "$group": {
                        "_id": {"$hour": {"date": "$created_at", "timezone": "-03:00"}},
                        "total": {"$sum": "$total"},
                    }
                },
                {"$sort": {"_id": 1}},
            ]
            trend_results = await orders_coll.aggregate(trend_pipe).to_list(None)
            for r in trend_results:
                hour_val = r.get("_id")
                try:
                    hour_int = int(hour_val) if hour_val is not None else 0
                    time_str = f"{hour_int:02d}:00"
                except (ValueError, TypeError):
                    time_str = f"{hour_val}:00" if hour_val else "00:00"
                trends.append({"time": time_str, "total": float(r.get("total", 0.0))})
        elif period == AnalyticsPeriod.WEEK:
            trend_pipe = [
                {"$match": match},
                {
                    "$group": {
                        "_id": {"$dayOfWeek": {"date": "$created_at", "timezone": "-03:00"}},
                        "total": {"$sum": "$total"},
                    }
                },
                {"$sort": {"_id": 1}},
            ]
            trend_results = await orders_coll.aggregate(trend_pipe).to_list(None)
            dow_names = {
                1: "Dom",
                2: "Seg",
                3: "Ter",
                4: "Qua",
                5: "Qui",
                6: "Sex",
                7: "Sáb",
            }
            trends = [
                {
                    "time": dow_names.get(r.get("_id"), str(r.get("_id"))),
                    "total": float(r.get("total", 0.0)),
                }
                for r in trend_results
            ]
        else:  # MONTH
            trend_pipe = [
                {"$match": match},
                {
                    "$group": {
                        "_id": {"$week": {"date": "$created_at", "timezone": "-03:00"}},
                        "total": {"$sum": "$total"},
                    }
                },
                {"$sort": {"_id": 1}},
            ]
            trend_results = await orders_coll.aggregate(trend_pipe).to_list(None)
            trends = [
                {"time": f"Semana {i + 1}", "total": float(r.get("total", 0.0))}
                for i, r in enumerate(trend_results)
            ]

        total_sales = stats[0]["total_sales"] if stats else 0
        total_orders = stats[0]["total_orders"] if stats else 0
        avg_ticket = stats[0]["avg_ticket"] if stats else 0

        return SalesReportData(
            period=period,
            total_sales=Decimal(str(total_sales)),
            total_orders=total_orders,
            average_ticket=Decimal(str(avg_ticket)),
            by_category={c["_id"]: Decimal(str(c["total"])) for c in by_cat},
            trends=trends,
        )

    async def get_order_insights(
        self,
        tenant_id: str,
        period: AnalyticsPeriod = AnalyticsPeriod.DAY,
        date_range: DateRange | None = None,
    ) -> OrderInsights:
        orders_coll = self._db["orders_read"]

        dr = self._resolve_date_range(period, date_range)
        match: dict[str, Any] = {
            "tenant_id": tenant_id,
            "created_at": {"$gte": dr.start, "$lte": dr.end},
        }

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

        # Heatmap (Hora vs. Dia da Semana)
        heatmap_pipe: list[dict[str, Any]] = [
            {"$match": match},
            {
                "$group": {
                    "_id": {
                        "dayOfWeek": {"$dayOfWeek": {"date": "$created_at", "timezone": "-03:00"}},
                        "hour": {"$hour": {"date": "$created_at", "timezone": "-03:00"}},
                    },
                    "total_sales": {"$sum": "$total"},
                    "orders_count": {"$sum": 1},
                }
            },
            {"$sort": {"_id.dayOfWeek": 1, "_id.hour": 1}},
        ]
        heatmap_results = await orders_coll.aggregate(heatmap_pipe).to_list(None)
        heatmap = [
            {
                "day_of_week": r["_id"].get("dayOfWeek"),
                "hour": r["_id"].get("hour"),
                "total_sales": float(r.get("total_sales") or 0.0),
                "orders_count": int(r.get("orders_count") or 0),
            }
            for r in heatmap_results
            if r.get("_id") is not None
        ]

        return OrderInsights(
            period=period,
            total_orders=total_orders,
            average_items_per_order=avg_items,
            peak_hour=peak_hour,
            heatmap=heatmap,
        )

    async def _get_throughput_trends(
        self,
        kitchen_coll: Any,
        tenant_id: str,
        period: AnalyticsPeriod,
        dr: DateRange,
    ) -> list[dict[str, Any]]:
        throughput_match = {
            "tenant_id": tenant_id,
            "state": "READY",
            "completed_at": {"$gte": dr.start, "$lte": dr.end},
        }
        throughput_trends: list[dict[str, Any]] = []
        if period == AnalyticsPeriod.DAY:
            throughput_pipe = [
                {"$match": throughput_match},
                {
                    "$group": {
                        "_id": {"$hour": {"date": "$completed_at", "timezone": "-03:00"}},
                        "count": {"$sum": 1},
                    }
                },
                {"$sort": {"_id": 1}},
            ]
            results = await kitchen_coll.aggregate(throughput_pipe).to_list(None)
            for r in results:
                h_val = r.get("_id")
                try:
                    h_int = int(h_val) if h_val is not None else 0
                    time_str = f"{h_int:02d}:00"
                except (ValueError, TypeError):
                    time_str = f"{h_val}:00" if h_val else "00:00"
                throughput_trends.append({"time": time_str, "count": int(r.get("count", 0))})
        elif period == AnalyticsPeriod.WEEK:
            throughput_pipe = [
                {"$match": throughput_match},
                {
                    "$group": {
                        "_id": {"$dayOfWeek": {"date": "$completed_at", "timezone": "-03:00"}},
                        "count": {"$sum": 1},
                    }
                },
                {"$sort": {"_id": 1}},
            ]
            results = await kitchen_coll.aggregate(throughput_pipe).to_list(None)
            dow_names = {1: "Dom", 2: "Seg", 3: "Ter", 4: "Qua", 5: "Qui", 6: "Sex", 7: "Sáb"}
            throughput_trends = [
                {
                    "time": dow_names.get(r.get("_id"), str(r.get("_id"))),
                    "count": int(r.get("count", 0)),
                }
                for r in results
            ]
        else:  # MONTH
            throughput_pipe = [
                {"$match": throughput_match},
                {
                    "$group": {
                        "_id": {"$week": {"date": "$completed_at", "timezone": "-03:00"}},
                        "count": {"$sum": 1},
                    }
                },
                {"$sort": {"_id": 1}},
            ]
            results = await kitchen_coll.aggregate(throughput_pipe).to_list(None)
            throughput_trends = [
                {"time": f"Semana {i + 1}", "count": int(r.get("count", 0))}
                for i, r in enumerate(results)
            ]
        return throughput_trends

    async def _get_bottlenecks(
        self,
        kitchen_coll: Any,
        tenant_id: str,
        dr: DateRange,
    ) -> list[dict[str, Any]]:
        bottleneck_pipe: list[dict[str, Any]] = [
            {
                "$match": {
                    "tenant_id": tenant_id,
                    "state": "READY",
                    "completed_at": {"$ne": None},
                    "started_at": {"$ne": None},
                    "created_at": {"$gte": dr.start, "$lte": dr.end},
                }
            },
            {
                "$group": {
                    "_id": "$name_cpy",
                    "avg_prep_time": {"$avg": {"$subtract": ["$completed_at", "$started_at"]}},
                    "items_prepared": {"$sum": 1},
                }
            },
            {"$sort": {"avg_prep_time": -1}},
            {"$limit": 5},
        ]
        bottleneck_results = await kitchen_coll.aggregate(bottleneck_pipe).to_list(None)
        return [
            {
                "name": r.get("_id") or "UNKNOWN",
                "average_prep_time_minutes": (r.get("avg_prep_time") or 0.0) / 60000,
                "items_prepared": r.get("items_prepared") or 0,
            }
            for r in bottleneck_results
        ]

    async def _get_queue_vs_prep_trends(
        self,
        kitchen_coll: Any,
        tenant_id: str,
        period: AnalyticsPeriod,
        dr: DateRange,
    ) -> list[dict[str, Any]]:
        qvp_match = {
            "tenant_id": tenant_id,
            "state": "READY",
            "completed_at": {"$ne": None},
            "started_at": {"$ne": None},
            "created_at": {"$gte": dr.start, "$lte": dr.end},
        }
        queue_vs_prep_trends: list[dict[str, Any]] = []
        if period == AnalyticsPeriod.DAY:
            qvp_pipe = [
                {"$match": qvp_match},
                {
                    "$group": {
                        "_id": {"$hour": {"date": "$completed_at", "timezone": "-03:00"}},
                        "avg_queue": {"$avg": {"$subtract": ["$started_at", "$created_at"]}},
                        "avg_prep": {"$avg": {"$subtract": ["$completed_at", "$started_at"]}},
                    }
                },
                {"$sort": {"_id": 1}},
            ]
            results = await kitchen_coll.aggregate(qvp_pipe).to_list(None)
            for r in results:
                h_val = r.get("_id")
                try:
                    h_int = int(h_val) if h_val is not None else 0
                    time_str = f"{h_int:02d}:00"
                except (ValueError, TypeError):
                    time_str = f"{h_val}:00" if h_val else "00:00"
                queue_vs_prep_trends.append(
                    {
                        "time": time_str,
                        "queue_minutes": (r.get("avg_queue") or 0.0) / 60000,
                        "prep_minutes": (r.get("avg_prep") or 0.0) / 60000,
                    }
                )
        elif period == AnalyticsPeriod.WEEK:
            qvp_pipe = [
                {"$match": qvp_match},
                {
                    "$group": {
                        "_id": {"$dayOfWeek": {"date": "$completed_at", "timezone": "-03:00"}},
                        "avg_queue": {"$avg": {"$subtract": ["$started_at", "$created_at"]}},
                        "avg_prep": {"$avg": {"$subtract": ["$completed_at", "$started_at"]}},
                    }
                },
                {"$sort": {"_id": 1}},
            ]
            results = await kitchen_coll.aggregate(qvp_pipe).to_list(None)
            dow_names = {1: "Dom", 2: "Seg", 3: "Ter", 4: "Qua", 5: "Qui", 6: "Sex", 7: "Sáb"}
            queue_vs_prep_trends = [
                {
                    "time": dow_names.get(r.get("_id"), str(r.get("_id"))),
                    "queue_minutes": (r.get("avg_queue") or 0.0) / 60000,
                    "prep_minutes": (r.get("avg_prep") or 0.0) / 60000,
                }
                for r in results
            ]
        else:
            qvp_pipe = [
                {"$match": qvp_match},
                {
                    "$group": {
                        "_id": {"$week": {"date": "$completed_at", "timezone": "-03:00"}},
                        "avg_queue": {"$avg": {"$subtract": ["$started_at", "$created_at"]}},
                        "avg_prep": {"$avg": {"$subtract": ["$completed_at", "$started_at"]}},
                    }
                },
                {"$sort": {"_id": 1}},
            ]
            results = await kitchen_coll.aggregate(qvp_pipe).to_list(None)
            queue_vs_prep_trends = [
                {
                    "time": f"Semana {i + 1}",
                    "queue_minutes": (r.get("avg_queue") or 0.0) / 60000,
                    "prep_minutes": (r.get("avg_prep") or 0.0) / 60000,
                }
                for i, r in enumerate(results)
            ]
        return queue_vs_prep_trends

    async def _get_cancelled_waste(
        self,
        kitchen_coll: Any,
        tenant_id: str,
        dr: DateRange,
    ) -> tuple[float, int]:
        waste_pipe: list[dict[str, Any]] = [
            {
                "$match": {
                    "tenant_id": tenant_id,
                    "state": "CANCELLED",
                    "created_at": {"$gte": dr.start, "$lte": dr.end},
                }
            },
            {
                "$lookup": {
                    "from": "orders_read",
                    "localField": "kitchen_item_id",
                    "foreignField": "items.id",
                    "as": "order_info",
                }
            },
            {"$unwind": {"path": "$order_info", "preserveNullAndEmptyArrays": True}},
            {"$unwind": {"path": "$order_info.items", "preserveNullAndEmptyArrays": True}},
            {
                "$project": {
                    "kitchen_item_id": 1,
                    "price": {
                        "$cond": [
                            {"$eq": ["$kitchen_item_id", "$order_info.items.id"]},
                            "$order_info.items.price",
                            0.0,
                        ]
                    },
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_waste": {"$sum": "$price"},
                    "count": {"$sum": 1},
                }
            },
        ]
        waste_results = await kitchen_coll.aggregate(waste_pipe).to_list(None)
        waste_val = 0.0
        waste_cnt = 0
        if waste_results:
            waste_val = float(waste_results[0].get("total_waste") or 0.0)
            waste_cnt = int(waste_results[0].get("count") or 0)
        return waste_val, waste_cnt

    async def get_kitchen_performance(
        self,
        tenant_id: str,
        period: AnalyticsPeriod = AnalyticsPeriod.DAY,
        date_range: DateRange | None = None,
    ) -> KitchenPerformance:
        kitchen_coll = self._db["kitchen_read"]

        dr = self._resolve_date_range(period, date_range)
        match: dict[str, Any] = {
            "tenant_id": tenant_id,
            "created_at": {"$gte": dr.start, "$lte": dr.end},
        }

        pipe: list[dict[str, Any]] = [
            {"$match": match},
            {
                "$group": {
                    "_id": None,
                    "avg_prep_time": {"$avg": {"$subtract": ["$completed_at", "$started_at"]}},
                    "avg_queue_time": {"$avg": {"$subtract": ["$started_at", "$created_at"]}},
                    "total_prepared": {"$sum": 1},
                    "completed": {"$sum": {"$cond": [{"$eq": ["$state", "READY"]}, 1, 0]}},
                    "completed_under_15": {
                        "$sum": {
                            "$cond": [
                                {
                                    "$and": [
                                        {"$eq": ["$state", "READY"]},
                                        {"$ne": ["$completed_at", None]},
                                        {"$ne": ["$started_at", None]},
                                        {
                                            "$lte": [
                                                {"$subtract": ["$completed_at", "$started_at"]},
                                                900000,
                                            ]
                                        },
                                    ]
                                },
                                1,
                                0,
                            ]
                        }
                    },
                    "std_dev_prep": {
                        "$stdDevPop": {
                            "$cond": [
                                {
                                    "$and": [
                                        {"$eq": ["$state", "READY"]},
                                        {"$ne": ["$completed_at", None]},
                                        {"$ne": ["$started_at", None]},
                                    ]
                                },
                                {"$subtract": ["$completed_at", "$started_at"]},
                                "$$REMOVE",
                            ]
                        }
                    },
                }
            },
        ]
        stats = await kitchen_coll.aggregate(pipe).to_list(None)

        by_station_pipe: list[dict[str, Any]] = [
            {"$match": match},
            {
                "$group": {
                    "_id": "$station_type_cpy",
                    "avg_prep_time": {"$avg": {"$subtract": ["$completed_at", "$started_at"]}},
                    "avg_queue_time": {"$avg": {"$subtract": ["$started_at", "$created_at"]}},
                    "total_prepared": {"$sum": 1},
                }
            },
        ]
        by_station_stats = await kitchen_coll.aggregate(by_station_pipe).to_list(None)

        by_station = {}
        for row in by_station_stats:
            station_name = row.get("_id") or "UNKNOWN"
            avg_prep = row.get("avg_prep_time")
            avg_queue = row.get("avg_queue_time")
            by_station[station_name] = {
                "average_prep_time_minutes": avg_prep / 60000 if avg_prep else 0.0,
                "average_queue_time_minutes": avg_queue / 60000 if avg_queue else 0.0,
                "items_prepared": row.get("total_prepared") or 0,
            }

        total_prepared = stats[0].get("total_prepared", 0) if stats else 0
        completed = stats[0].get("completed", 0) if stats else 0
        avg_prep_ms = stats[0].get("avg_prep_time", 0.0) if stats else 0.0
        avg_queue_ms = stats[0].get("avg_queue_time", 0.0) if stats else 0.0
        completion_rate = completed / total_prepared if total_prepared > 0 else 0.0

        completed_under_15 = stats[0].get("completed_under_15", 0) if stats else 0
        sla_compliance_rate = completed_under_15 / completed if completed > 0 else 0.0

        std_dev_prep_ms = stats[0].get("std_dev_prep", 0.0) if stats else 0.0
        if std_dev_prep_ms is None:
            std_dev_prep_ms = 0.0

        throughput_trends = await self._get_throughput_trends(kitchen_coll, tenant_id, period, dr)
        bottlenecks = await self._get_bottlenecks(kitchen_coll, tenant_id, dr)
        queue_vs_prep_trends = await self._get_queue_vs_prep_trends(
            kitchen_coll, tenant_id, period, dr
        )
        waste_val, waste_cnt = await self._get_cancelled_waste(kitchen_coll, tenant_id, dr)

        return KitchenPerformance(
            period=period,
            average_prep_time_minutes=avg_prep_ms / 60000 if avg_prep_ms else 0.0,
            average_queue_time_minutes=avg_queue_ms / 60000 if avg_queue_ms else 0.0,
            items_prepared=total_prepared,
            completion_rate=completion_rate,
            by_station=by_station,
            sla_compliance_rate=sla_compliance_rate,
            bottlenecks=bottlenecks,
            throughput_trends=throughput_trends,
            std_dev_prep_time_minutes=std_dev_prep_ms / 60000 if std_dev_prep_ms else 0.0,
            queue_vs_prep_trends=queue_vs_prep_trends,
            waste_cancelled_value=waste_val,
            waste_cancelled_count=waste_cnt,
        )

    async def get_menu_items_sales(
        self,
        tenant_id: str,
        period: AnalyticsPeriod = AnalyticsPeriod.DAY,
        date_range: DateRange | None = None,
    ) -> list[dict[str, Any]]:
        orders_coll = self._db["orders_read"]
        dr = self._resolve_date_range(period, date_range)
        match: dict[str, Any] = {
            "tenant_id": tenant_id,
            "created_at": {"$gte": dr.start, "$lte": dr.end},
        }
        pipe: list[dict[str, Any]] = [
            {"$match": match},
            {"$unwind": "$items"},
            {
                "$group": {
                    "_id": "$items.menu_item_id",
                    "name": {"$first": "$items.name"},
                    "quantity": {"$sum": "$items.quantity"},
                    "revenue": {"$sum": "$items.subtotal"},
                }
            },
        ]
        return await orders_coll.aggregate(pipe).to_list(None)

    async def get_demand_forecast(self, tenant_id: str) -> list[dict[str, Any]]:
        orders_coll = self._db["orders_read"]
        now = datetime.now(UTC)
        start_date = now - timedelta(days=30)
        current_day_of_week = now.isoweekday()  # Monday=1, Sunday=7

        # Map isoweekday() to MongoDB $dayOfWeek:
        # iso: 1 (Mon) -> mongo: 2
        # iso: 7 (Sun) -> mongo: 1
        days_in_week = 7
        mongo_day_of_week = current_day_of_week + 1
        if mongo_day_of_week > days_in_week:
            mongo_day_of_week = 1

        pipe = [
            {
                "$match": {
                    "tenant_id": tenant_id,
                    "created_at": {"$gte": start_date},
                }
            },
            {
                "$project": {
                    "total": 1,
                    "created_at": 1,
                    "day_of_week": {"$dayOfWeek": {"date": "$created_at", "timezone": "-03:00"}},
                    "hour": {"$hour": {"date": "$created_at", "timezone": "-03:00"}},
                    "date_str": {
                        "$dateToString": {
                            "format": "%Y-%m-%d",
                            "date": "$created_at",
                            "timezone": "-03:00",
                        }
                    },
                }
            },
            {"$match": {"day_of_week": mongo_day_of_week}},
            {
                "$group": {
                    "_id": {"hour": "$hour", "date_str": "$date_str"},
                    "daily_hour_total": {"$sum": "$total"},
                }
            },
            {"$group": {"_id": "$_id.hour", "avg_total": {"$avg": "$daily_hour_total"}}},
            {"$sort": {"_id": 1}},
        ]
        results = await orders_coll.aggregate(pipe).to_list(None)

        forecast = []
        for h in range(24):
            match = next((r for r in results if r["_id"] == h), None)
            val = float(match["avg_total"]) if match else 0.0
            forecast.append({"time": f"{h:02d}:00", "total": round(val, 2)})
        return forecast

    async def get_order_funnel(
        self,
        tenant_id: str,
        period: AnalyticsPeriod = AnalyticsPeriod.DAY,
        date_range: DateRange | None = None,
    ) -> dict[str, Any]:
        kitchen_coll = self._db["kitchen_read"]
        dr = self._resolve_date_range(period, date_range)

        # 1. Queue and Prep times from KDS
        kds_match = {
            "tenant_id": tenant_id,
            "created_at": {"$gte": dr.start, "$lte": dr.end},
        }
        kds_pipe = [
            {"$match": kds_match},
            {
                "$group": {
                    "_id": None,
                    "avg_queue_ms": {"$avg": {"$subtract": ["$started_at", "$created_at"]}},
                    "avg_prep_ms": {"$avg": {"$subtract": ["$completed_at", "$started_at"]}},
                    "total_items": {"$sum": 1},
                }
            },
        ]
        kds_res = await kitchen_coll.aggregate(kds_pipe).to_list(None)

        avg_queue_min = 0.0
        avg_prep_min = 0.0
        if kds_res and kds_res[0]:
            q_ms = kds_res[0].get("avg_queue_ms")
            p_ms = kds_res[0].get("avg_prep_ms")
            avg_queue_min = q_ms / 60000 if q_ms else 0.0
            avg_prep_min = p_ms / 60000 if p_ms else 0.0

        # 2. Complete order lifecycle (creation to checkout/closing)
        hist_pipe = [
            {"$match": {"tenant_id": tenant_id, "created_at": {"$gte": dr.start, "$lte": dr.end}}},
            {
                "$lookup": {
                    "from": "order_history",
                    "localField": "order_id",
                    "foreignField": "order_id",
                    "as": "history",
                }
            },
            {"$unwind": "$history"},
            {
                "$project": {
                    "order_id": 1,
                    "created_at": 1,
                    "closed_at": {"$dateFromString": {"dateString": "$history.closed_at"}},
                }
            },
            {
                "$group": {
                    "_id": None,
                    "avg_total_cycle_ms": {"$avg": {"$subtract": ["$closed_at", "$created_at"]}},
                }
            },
        ]
        hist_res = await self._db["orders_read"].aggregate(hist_pipe).to_list(None)
        avg_total_cycle_min = 0.0
        if hist_res and hist_res[0]:
            cycle_ms = hist_res[0].get("avg_total_cycle_ms")
            avg_total_cycle_min = cycle_ms / 60000 if cycle_ms else 0.0

        avg_checkout_min = max(0.0, avg_total_cycle_min - (avg_queue_min + avg_prep_min))
        if avg_total_cycle_min == 0.0:
            avg_checkout_min = 5.0
            avg_total_cycle_min = avg_queue_min + avg_prep_min + avg_checkout_min

        return {
            "avg_queue_minutes": round(avg_queue_min, 1),
            "avg_prep_minutes": round(avg_prep_min, 1),
            "avg_checkout_minutes": round(avg_checkout_min, 1),
            "avg_total_cycle_minutes": round(avg_total_cycle_min, 1),
        }

    async def get_table_performance(
        self,
        tenant_id: str,
        period: AnalyticsPeriod = AnalyticsPeriod.DAY,
        date_range: DateRange | None = None,
    ) -> list[dict[str, Any]]:
        history_coll = self._db["order_history"]
        dr = self._resolve_date_range(period, date_range)

        pipe = [
            {
                "$project": {
                    "tenant_id": 1,
                    "total": 1,
                    "fulfillment": 1,
                    "closed_at_date": {"$dateFromString": {"dateString": "$closed_at"}},
                }
            },
            {
                "$match": {
                    "tenant_id": tenant_id,
                    "closed_at_date": {"$gte": dr.start, "$lte": dr.end},
                    "fulfillment.type": "TABLE",
                    "fulfillment.table.table_number": {"$ne": None},
                }
            },
            {
                "$group": {
                    "_id": "$fulfillment.table.table_number",
                    "total_revenue": {"$sum": {"$toDouble": "$total"}},
                    "orders_count": {"$sum": 1},
                    "avg_ticket": {"$avg": {"$toDouble": "$total"}},
                }
            },
            {"$sort": {"_id": 1}},
        ]
        results = await history_coll.aggregate(pipe).to_list(None)
        return [
            {
                "table_number": r["_id"],
                "total_revenue": round(r["total_revenue"], 2),
                "orders_count": r["orders_count"],
                "avg_ticket": round(r["avg_ticket"], 2),
            }
            for r in results
        ]

    async def get_combo_recommendations(self, tenant_id: str) -> list[dict[str, Any]]:
        history_coll = self._db["order_history"]
        cursor = history_coll.find({"tenant_id": tenant_id}, {"items": 1})
        orders = await cursor.to_list(length=200)

        pair_counts: dict[tuple[str, str], int] = {}
        item_counts: dict[str, int] = {}

        for o in orders:
            items = o.get("items", [])
            names = list({item.get("name") for item in items if item.get("name")})
            for name in names:
                item_counts[name] = item_counts.get(name, 0) + 1
            for i in range(len(names)):
                for j in range(i + 1, len(names)):
                    sorted_pair = sorted([names[i], names[j]])
                    pair = (sorted_pair[0], sorted_pair[1])
                    pair_counts[pair] = pair_counts.get(pair, 0) + 1

        total_orders = len(orders)
        if total_orders == 0:
            return []

        recommendations = []
        for pair, count in pair_counts.items():
            item_a, item_b = pair
            support = count / total_orders
            conf_a = count / item_counts[item_a] if item_counts[item_a] > 0 else 0.0
            conf_b = count / item_counts[item_b] if item_counts[item_b] > 0 else 0.0

            recommendations.append(
                {
                    "item_a": item_a,
                    "item_b": item_b,
                    "co_occurrences": count,
                    "support": round(support, 3),
                    "confidence_a_to_b": round(conf_a, 3),
                    "confidence_b_to_a": round(conf_b, 3),
                }
            )

        def get_co_occurrences(x: dict[str, Any]) -> int:
            return int(x["co_occurrences"])

        recommendations.sort(key=get_co_occurrences, reverse=True)
        return recommendations[:10]

    async def get_cannibalization_warnings(self, tenant_id: str) -> list[dict[str, Any]]:
        orders_coll = self._db["orders_read"]
        now = datetime.now(UTC)

        cw_start = now - timedelta(days=7)
        pw_start = now - timedelta(days=14)

        cw_pipe = [
            {"$match": {"tenant_id": tenant_id, "created_at": {"$gte": cw_start, "$lte": now}}},
            {"$unwind": "$items"},
            {
                "$group": {
                    "_id": {
                        "menu_item_id": "$items.menu_item_id",
                        "name": "$items.name",
                        "category": "$items.category",
                    },
                    "qty": {"$sum": "$items.quantity"},
                }
            },
        ]
        cw_res = await orders_coll.aggregate(cw_pipe).to_list(None)

        pw_pipe = [
            {"$match": {"tenant_id": tenant_id, "created_at": {"$gte": pw_start, "$lt": cw_start}}},
            {"$unwind": "$items"},
            {
                "$group": {
                    "_id": {
                        "menu_item_id": "$items.menu_item_id",
                        "name": "$items.name",
                        "category": "$items.category",
                    },
                    "qty": {"$sum": "$items.quantity"},
                }
            },
        ]
        pw_res = await orders_coll.aggregate(pw_pipe).to_list(None)
        return self._analyze_cannibalization(cw_res, pw_res)

    def _build_sales_stats(
        self, cw_res: list[dict[str, Any]], pw_res: list[dict[str, Any]]
    ) -> dict[int, dict[str, Any]]:
        stats: dict[int, dict[str, Any]] = {}
        for r in cw_res:
            item_id = r["_id"]["menu_item_id"]
            stats[item_id] = {
                "name": r["_id"]["name"],
                "category": r["_id"]["category"],
                "cw_qty": r["qty"],
                "pw_qty": 0,
            }
        for r in pw_res:
            item_id = r["_id"]["menu_item_id"]
            if item_id in stats:
                stats[item_id]["pw_qty"] = r["qty"]
            else:
                stats[item_id] = {
                    "name": r["_id"]["name"],
                    "category": r["_id"]["category"],
                    "cw_qty": 0,
                    "pw_qty": r["qty"],
                }
        return stats

    def _find_growing_and_shrinking(
        self, items: list[dict[str, Any]], min_qty: int, pct_limit: float
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        losers = []
        winners = []
        for item in items:
            cw = item["cw_qty"]
            pw = item["pw_qty"]
            diff = cw - pw

            if pw >= min_qty and diff <= -min_qty:
                pct_change = diff / pw
                if pct_change <= -pct_limit:
                    item["pct_change"] = pct_change
                    item["diff"] = diff
                    losers.append(item)
            elif cw >= min_qty and diff >= min_qty:
                pct_change = diff / pw if pw > 0 else 1.0
                if pct_change >= pct_limit:
                    item["pct_change"] = pct_change
                    item["diff"] = diff
                    winners.append(item)
        return losers, winners

    def _analyze_cannibalization(
        self, cw_res: list[dict[str, Any]], pw_res: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        min_qty = 3
        pct_limit = 0.2
        high_conf_threshold = 5

        stats = self._build_sales_stats(cw_res, pw_res)

        by_category: dict[str, list[dict[str, Any]]] = {}
        for item_id, info in stats.items():
            cat = info["category"] or "Outros"
            info["item_id"] = item_id
            by_category.setdefault(cat, []).append(info)

        warnings: list[dict[str, Any]] = []
        for cat, items in by_category.items():
            losers, winners = self._find_growing_and_shrinking(items, min_qty, pct_limit)

            for loser in losers:
                for winner in winners:
                    conf = (
                        "HIGH"
                        if abs(loser["diff"]) >= high_conf_threshold
                        and winner["diff"] >= high_conf_threshold
                        else "MEDIUM"
                    )
                    warnings.append(
                        {
                            "category": cat,
                            "cannibalized_item_name": loser["name"],
                            "cannibalized_item_id": loser["item_id"],
                            "cannibalized_drop": loser["diff"],
                            "cannibalized_pct": round(loser["pct_change"] * 100, 1),
                            "growing_item_name": winner["name"],
                            "growing_item_id": winner["item_id"],
                            "growing_rise": winner["diff"],
                            "growing_pct": round(winner["pct_change"] * 100, 1),
                            "confidence": conf,
                        }
                    )

        return warnings
