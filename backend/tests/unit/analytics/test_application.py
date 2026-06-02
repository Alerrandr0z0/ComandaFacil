from __future__ import annotations

import datetime
from decimal import Decimal

import pytest

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
from app.analytics.domain.value_objects import (
    DashboardData,
    DateRange,
    KitchenPerformance,
    OrderInsights,
    SalesReportData,
)


class InMemoryAnalyticsRepository:
    def __init__(self) -> None:
        self._dashboard: DashboardData | None = None
        self._sales: SalesReportData | None = None
        self._orders: OrderInsights | None = None
        self._kitchen: KitchenPerformance | None = None
        self.last_tenant_id: str | None = None
        self.last_period: AnalyticsPeriod | None = None
        self.last_date_range: DateRange | None = None

    async def get_dashboard(
        self,
        tenant_id: str,
        period: AnalyticsPeriod = AnalyticsPeriod.DAY,
        date_range: DateRange | None = None,
    ) -> DashboardData:
        self.last_tenant_id = tenant_id
        self.last_period = period
        self.last_date_range = date_range
        assert self._dashboard is not None
        return self._dashboard

    async def get_sales_report(
        self,
        tenant_id: str,
        period: AnalyticsPeriod = AnalyticsPeriod.DAY,
        date_range: DateRange | None = None,
    ) -> SalesReportData:
        self.last_tenant_id = tenant_id
        self.last_period = period
        self.last_date_range = date_range
        assert self._sales is not None
        return self._sales

    async def get_order_insights(
        self,
        tenant_id: str,
        period: AnalyticsPeriod = AnalyticsPeriod.DAY,
        date_range: DateRange | None = None,
    ) -> OrderInsights:
        self.last_tenant_id = tenant_id
        self.last_period = period
        self.last_date_range = date_range
        assert self._orders is not None
        return self._orders

    async def get_kitchen_performance(
        self,
        tenant_id: str,
        period: AnalyticsPeriod = AnalyticsPeriod.DAY,
        date_range: DateRange | None = None,
    ) -> KitchenPerformance:
        self.last_tenant_id = tenant_id
        self.last_period = period
        self.last_date_range = date_range
        assert self._kitchen is not None
        return self._kitchen


# ─── Happy path: data exists ─────────────────────────────────────────────────


@pytest.mark.unit
async def test_get_dashboard_when_data_exists_then_returns() -> None:
    repo = InMemoryAnalyticsRepository()
    expected = DashboardData(
        total_sales=Decimal("2000.00"),
        orders_count=50,
        average_ticket=Decimal("40.00"),
        low_stock_items=1,
        average_prep_time_minutes=8.0,
    )
    repo._dashboard = expected
    handler = GetDashboardHandler(repo)
    query = GetDashboardQuery(tenant_id="t1")

    result = await handler.handle(query)

    assert result == expected
    assert result.orders_count == 50


@pytest.mark.unit
async def test_get_sales_report_when_data_exists_then_returns() -> None:
    repo = InMemoryAnalyticsRepository()
    expected = SalesReportData(
        period=AnalyticsPeriod.MONTH,
        total_sales=Decimal("30000.00"),
        total_orders=800,
        average_ticket=Decimal("37.50"),
        by_category={"BEBIDAS": Decimal("10000.00")},
    )
    repo._sales = expected
    handler = GetSalesReportHandler(repo)
    query = GetSalesReportQuery(tenant_id="t1", period=AnalyticsPeriod.MONTH)

    result = await handler.handle(query)

    assert result == expected
    assert result.total_orders == 800


@pytest.mark.unit
async def test_get_order_insights_when_data_exists_then_returns() -> None:
    repo = InMemoryAnalyticsRepository()
    expected = OrderInsights(
        period=AnalyticsPeriod.WEEK,
        total_orders=350,
        average_items_per_order=2.4,
        peak_hour=19,
    )
    repo._orders = expected
    handler = GetOrderInsightsHandler(repo)
    query = GetOrderInsightsQuery(tenant_id="t1", period=AnalyticsPeriod.WEEK)

    result = await handler.handle(query)

    assert result == expected
    assert result.peak_hour == 19


@pytest.mark.unit
async def test_get_kitchen_performance_when_data_exists_then_returns() -> None:
    repo = InMemoryAnalyticsRepository()
    expected = KitchenPerformance(
        period=AnalyticsPeriod.DAY,
        average_prep_time_minutes=8.5,
        items_prepared=200,
        completion_rate=0.95,
    )
    repo._kitchen = expected
    handler = GetKitchenPerformanceHandler(repo)
    query = GetKitchenPerformanceQuery(tenant_id="t1")

    result = await handler.handle(query)
    assert result == expected
    assert result.items_prepared == 200


# ─── Param passthrough ────────────────────────────────────────────────────────


@pytest.mark.unit
async def test_get_dashboard_when_tenant_id_then_passed_to_repo() -> None:
    repo = InMemoryAnalyticsRepository()
    repo._dashboard = DashboardData(
        total_sales=Decimal("0"),
        orders_count=0,
        average_ticket=Decimal("0"),
        low_stock_items=0,
        average_prep_time_minutes=0.0,
    )
    handler = GetDashboardHandler(repo)
    query = GetDashboardQuery(tenant_id="tenant_abc")

    await handler.handle(query)

    assert repo.last_tenant_id == "tenant_abc"


@pytest.mark.unit
async def test_get_dashboard_when_period_then_passed_to_repo() -> None:
    repo = InMemoryAnalyticsRepository()
    repo._dashboard = DashboardData(
        total_sales=Decimal("0"),
        orders_count=0,
        average_ticket=Decimal("0"),
        low_stock_items=0,
        average_prep_time_minutes=0.0,
    )
    handler = GetDashboardHandler(repo)
    query = GetDashboardQuery(tenant_id="t1", period=AnalyticsPeriod.MONTH)

    await handler.handle(query)

    assert repo.last_period == AnalyticsPeriod.MONTH


@pytest.mark.unit
async def test_get_dashboard_when_date_range_then_passed_to_repo() -> None:
    repo = InMemoryAnalyticsRepository()
    repo._dashboard = DashboardData(
        total_sales=Decimal("0"),
        orders_count=0,
        average_ticket=Decimal("0"),
        low_stock_items=0,
        average_prep_time_minutes=0.0,
    )
    handler = GetDashboardHandler(repo)
    date_range = DateRange(
        start=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
        end=datetime.datetime(2026, 1, 31, tzinfo=datetime.UTC),
    )
    query = GetDashboardQuery(tenant_id="t1", date_range=date_range)

    await handler.handle(query)

    assert repo.last_date_range == date_range


@pytest.mark.unit
async def test_get_dashboard_when_default_period_then_day() -> None:
    repo = InMemoryAnalyticsRepository()
    repo._dashboard = DashboardData(
        total_sales=Decimal("0"),
        orders_count=0,
        average_ticket=Decimal("0"),
        low_stock_items=0,
        average_prep_time_minutes=0.0,
    )
    handler = GetDashboardHandler(repo)
    query = GetDashboardQuery(tenant_id="t1")

    await handler.handle(query)

    assert repo.last_period == AnalyticsPeriod.DAY


@pytest.mark.unit
async def test_get_dashboard_when_default_date_range_then_none() -> None:
    repo = InMemoryAnalyticsRepository()
    repo._dashboard = DashboardData(
        total_sales=Decimal("0"),
        orders_count=0,
        average_ticket=Decimal("0"),
        low_stock_items=0,
        average_prep_time_minutes=0.0,
    )
    handler = GetDashboardHandler(repo)
    query = GetDashboardQuery(tenant_id="t1")

    await handler.handle(query)

    assert repo.last_date_range is None


# ─── All handlers passthrough tenant_id ───────────────────────────────────────


@pytest.mark.unit
@pytest.mark.parametrize(
    ("handler_cls", "query_cls", "field"),
    [
        (GetDashboardHandler, GetDashboardQuery, "dashboard"),
        (GetSalesReportHandler, GetSalesReportQuery, "sales"),
        (GetOrderInsightsHandler, GetOrderInsightsQuery, "orders"),
        (GetKitchenPerformanceHandler, GetKitchenPerformanceQuery, "kitchen"),
    ],
)
async def test_all_handlers_when_tenant_id_then_passed_to_repo(
    handler_cls: type,
    query_cls: type,
    field: str,
) -> None:
    repo = InMemoryAnalyticsRepository()
    repo._dashboard = DashboardData(
        total_sales=Decimal("0"),
        orders_count=0,
        average_ticket=Decimal("0"),
        low_stock_items=0,
        average_prep_time_minutes=0.0,
    )
    repo._sales = SalesReportData(
        period=AnalyticsPeriod.DAY,
        total_sales=Decimal("0"),
        total_orders=0,
        average_ticket=Decimal("0"),
    )
    repo._orders = OrderInsights(
        period=AnalyticsPeriod.DAY,
        total_orders=0,
        average_items_per_order=0.0,
        peak_hour=0,
    )
    repo._kitchen = KitchenPerformance(
        period=AnalyticsPeriod.DAY,
        average_prep_time_minutes=0.0,
        items_prepared=0,
        completion_rate=0.0,
    )
    handler = handler_cls(repo)
    query = query_cls(tenant_id="tenant_passthrough")

    await handler.handle(query)

    assert repo.last_tenant_id == "tenant_passthrough"
