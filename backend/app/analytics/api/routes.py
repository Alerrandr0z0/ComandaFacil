import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query

from app.analytics.application.queries import (
    GetDashboardHandler,
    GetDashboardQuery,
    GetKitchenPerformanceHandler,
    GetKitchenPerformanceQuery,
    GetMenuMatrixHandler,
    GetMenuMatrixQuery,
    GetOrderInsightsHandler,
    GetOrderInsightsQuery,
    GetSalesReportHandler,
    GetSalesReportQuery,
)
from app.analytics.domain.enums import AnalyticsPeriod
from app.analytics.domain.value_objects import DateRange
from app.analytics.infrastructure.mongo_repository import MongoAnalyticsRepository
from app.dependencies import CurrentTenantId, DbSession, MongoDB, require_permission
from app.stock.infrastructure.pg_repository import (
    SQLAlchemyRecipeRepository,
    SQLAlchemyStockItemRepository,
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def _parse_date_range(
    start_date: str | None, end_date: str | None
) -> DateRange | None:
    if not start_date:
        return None
    
    try:
        start = datetime.datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        if end_date:
            end = datetime.datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        else:
            end = datetime.datetime.now(datetime.UTC)
        return DateRange(start=start, end=end)
    except ValueError:
        return None


@router.get("/dashboard", dependencies=[Depends(require_permission("VIEW_ANALYTICS"))])
async def get_dashboard(
    tenant_id: CurrentTenantId,
    mongo: MongoDB,
    period: AnalyticsPeriod = Query(default=AnalyticsPeriod.DAY),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
) -> dict[str, Any]:
    repo = MongoAnalyticsRepository(mongo)
    handler = GetDashboardHandler(repo)
    date_range = _parse_date_range(start_date, end_date)
    data = await handler.handle(GetDashboardQuery(tenant_id=tenant_id, period=period, date_range=date_range))
    return {
        "total_sales": str(data.total_sales),
        "orders_count": data.orders_count,
        "average_ticket": str(data.average_ticket),
        "low_stock_items": data.low_stock_items,
        "average_prep_time_minutes": data.average_prep_time_minutes,
    }


@router.get("/sales", dependencies=[Depends(require_permission("VIEW_ANALYTICS"))])
async def get_sales_report(
    tenant_id: CurrentTenantId,
    mongo: MongoDB,
    period: AnalyticsPeriod = Query(default=AnalyticsPeriod.DAY),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
) -> dict[str, Any]:
    repo = MongoAnalyticsRepository(mongo)
    handler = GetSalesReportHandler(repo)
    date_range = _parse_date_range(start_date, end_date)
    data = await handler.handle(GetSalesReportQuery(tenant_id=tenant_id, period=period, date_range=date_range))
    return {
        "period": data.period.value,
        "total_sales": str(data.total_sales),
        "total_orders": data.total_orders,
        "average_ticket": str(data.average_ticket),
        "by_category": {k: str(v) for k, v in data.by_category.items()},
        "trends": data.trends,
    }


@router.get("/orders", dependencies=[Depends(require_permission("VIEW_ANALYTICS"))])
async def get_order_insights(
    tenant_id: CurrentTenantId,
    mongo: MongoDB,
    period: AnalyticsPeriod = Query(default=AnalyticsPeriod.DAY),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
) -> dict[str, Any]:
    repo = MongoAnalyticsRepository(mongo)
    handler = GetOrderInsightsHandler(repo)
    date_range = _parse_date_range(start_date, end_date)
    data = await handler.handle(GetOrderInsightsQuery(tenant_id=tenant_id, period=period, date_range=date_range))
    return {
        "period": data.period.value,
        "total_orders": data.total_orders,
        "average_items_per_order": data.average_items_per_order,
        "peak_hour": data.peak_hour,
        "heatmap": data.heatmap,
    }


@router.get("/kitchen", dependencies=[Depends(require_permission("VIEW_ANALYTICS"))])
async def get_kitchen_performance(
    tenant_id: CurrentTenantId,
    mongo: MongoDB,
    period: AnalyticsPeriod = Query(default=AnalyticsPeriod.DAY),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
) -> dict[str, Any]:
    repo = MongoAnalyticsRepository(mongo)
    handler = GetKitchenPerformanceHandler(repo)
    date_range = _parse_date_range(start_date, end_date)
    data = await handler.handle(GetKitchenPerformanceQuery(tenant_id=tenant_id, period=period, date_range=date_range))
    return {
        "period": data.period.value,
        "average_prep_time_minutes": data.average_prep_time_minutes,
        "average_queue_time_minutes": data.average_queue_time_minutes,
        "items_prepared": data.items_prepared,
        "completion_rate": data.completion_rate,
        "by_station": data.by_station,
        "sla_compliance_rate": data.sla_compliance_rate,
        "bottlenecks": data.bottlenecks,
        "throughput_trends": data.throughput_trends,
        "std_dev_prep_time_minutes": data.std_dev_prep_time_minutes,
        "queue_vs_prep_trends": data.queue_vs_prep_trends,
        "waste_cancelled_value": data.waste_cancelled_value,
        "waste_cancelled_count": data.waste_cancelled_count,
    }


@router.get("/menu-matrix", dependencies=[Depends(require_permission("VIEW_ANALYTICS"))])
async def get_menu_matrix(
    tenant_id: CurrentTenantId,
    mongo: MongoDB,
    db: DbSession,
    period: AnalyticsPeriod = Query(default=AnalyticsPeriod.DAY),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
) -> dict[str, Any]:
    analytics_repo = MongoAnalyticsRepository(mongo)
    item_repo = SQLAlchemyStockItemRepository(db)
    recipe_repo = SQLAlchemyRecipeRepository(db, item_repo)

    date_range = _parse_date_range(start_date, end_date)
    handler = GetMenuMatrixHandler(analytics_repo, recipe_repo)
    return await handler.handle(GetMenuMatrixQuery(tenant_id=tenant_id, period=period, date_range=date_range))


@router.get("/demand-forecast", dependencies=[Depends(require_permission("VIEW_ANALYTICS"))])
async def get_demand_forecast(
    tenant_id: CurrentTenantId,
    mongo: MongoDB,
) -> list[dict[str, Any]]:
    repo = MongoAnalyticsRepository(mongo)
    return await repo.get_demand_forecast(tenant_id)


@router.get("/order-funnel", dependencies=[Depends(require_permission("VIEW_ANALYTICS"))])
async def get_order_funnel(
    tenant_id: CurrentTenantId,
    mongo: MongoDB,
    period: AnalyticsPeriod = Query(default=AnalyticsPeriod.DAY),
) -> dict[str, Any]:
    repo = MongoAnalyticsRepository(mongo)
    return await repo.get_order_funnel(tenant_id, period)


@router.get("/table-performance", dependencies=[Depends(require_permission("VIEW_ANALYTICS"))])
async def get_table_performance(
    tenant_id: CurrentTenantId,
    mongo: MongoDB,
    period: AnalyticsPeriod = Query(default=AnalyticsPeriod.DAY),
) -> list[dict[str, Any]]:
    repo = MongoAnalyticsRepository(mongo)
    return await repo.get_table_performance(tenant_id, period)


@router.get("/combo-recommendations", dependencies=[Depends(require_permission("VIEW_ANALYTICS"))])
async def get_combo_recommendations(
    tenant_id: CurrentTenantId,
    mongo: MongoDB,
) -> list[dict[str, Any]]:
    repo = MongoAnalyticsRepository(mongo)
    return await repo.get_combo_recommendations(tenant_id)


@router.get(
    "/cannibalization-warnings", dependencies=[Depends(require_permission("VIEW_ANALYTICS"))]
)
async def get_cannibalization_warnings(
    tenant_id: CurrentTenantId,
    mongo: MongoDB,
) -> list[dict[str, Any]]:
    repo = MongoAnalyticsRepository(mongo)
    return await repo.get_cannibalization_warnings(tenant_id)
