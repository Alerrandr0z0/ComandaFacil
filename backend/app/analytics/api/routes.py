from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from app.analytics.application.queries import (
    GetDashboardHandler,
    GetDashboardQuery,
    GetKitchenPerformanceHandler,
    GetKitchenPerformanceQuery,
    GetOrderInsightsHandler,
    GetOrderInsightsQuery,
    GetSalesReportHandler,
    GetSalesReportQuery,
)
from app.analytics.domain.enums import AnalyticsPeriod
from app.analytics.infrastructure.mongo_repository import MongoAnalyticsRepository
from app.dependencies import CurrentTenantId, MongoDB

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/dashboard")
async def get_dashboard(
    tenant_id: CurrentTenantId,
    mongo: MongoDB,
    period: AnalyticsPeriod = Query(default=AnalyticsPeriod.DAY),
) -> dict[str, Any]:
    repo = MongoAnalyticsRepository(mongo)
    handler = GetDashboardHandler(repo)
    data = await handler.handle(GetDashboardQuery(tenant_id=tenant_id, period=period))
    return {
        "total_sales": str(data.total_sales),
        "orders_count": data.orders_count,
        "average_ticket": str(data.average_ticket),
        "low_stock_items": data.low_stock_items,
        "average_prep_time_minutes": data.average_prep_time_minutes,
    }


@router.get("/sales")
async def get_sales_report(
    tenant_id: CurrentTenantId,
    mongo: MongoDB,
    period: AnalyticsPeriod = Query(default=AnalyticsPeriod.DAY),
) -> dict[str, Any]:
    repo = MongoAnalyticsRepository(mongo)
    handler = GetSalesReportHandler(repo)
    data = await handler.handle(GetSalesReportQuery(tenant_id=tenant_id, period=period))
    return {
        "period": data.period.value,
        "total_sales": str(data.total_sales),
        "total_orders": data.total_orders,
        "average_ticket": str(data.average_ticket),
        "by_category": {k: str(v) for k, v in data.by_category.items()},
    }


@router.get("/orders")
async def get_order_insights(
    tenant_id: CurrentTenantId,
    mongo: MongoDB,
    period: AnalyticsPeriod = Query(default=AnalyticsPeriod.DAY),
) -> dict[str, Any]:
    repo = MongoAnalyticsRepository(mongo)
    handler = GetOrderInsightsHandler(repo)
    data = await handler.handle(GetOrderInsightsQuery(tenant_id=tenant_id, period=period))
    return {
        "period": data.period.value,
        "total_orders": data.total_orders,
        "average_items_per_order": data.average_items_per_order,
        "peak_hour": data.peak_hour,
    }


@router.get("/kitchen")
async def get_kitchen_performance(
    tenant_id: CurrentTenantId,
    mongo: MongoDB,
    period: AnalyticsPeriod = Query(default=AnalyticsPeriod.DAY),
) -> dict[str, Any]:
    repo = MongoAnalyticsRepository(mongo)
    handler = GetKitchenPerformanceHandler(repo)
    data = await handler.handle(GetKitchenPerformanceQuery(tenant_id=tenant_id, period=period))
    return {
        "period": data.period.value,
        "average_prep_time_minutes": data.average_prep_time_minutes,
        "items_prepared": data.items_prepared,
        "completion_rate": data.completion_rate,
    }
