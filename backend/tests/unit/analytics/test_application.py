from __future__ import annotations

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

    async def get_dashboard(
        self,
        tenant_id: str,
        period: AnalyticsPeriod = AnalyticsPeriod.DAY,
        date_range: object = None,
    ) -> DashboardData:
        assert self._dashboard is not None
        return self._dashboard

    async def get_sales_report(
        self,
        tenant_id: str,
        period: AnalyticsPeriod = AnalyticsPeriod.DAY,
        date_range: object = None,
    ) -> SalesReportData:
        assert self._sales is not None
        return self._sales

    async def get_order_insights(
        self,
        tenant_id: str,
        period: AnalyticsPeriod = AnalyticsPeriod.DAY,
        date_range: object = None,
    ) -> OrderInsights:
        assert self._orders is not None
        return self._orders

    async def get_kitchen_performance(
        self,
        tenant_id: str,
        period: AnalyticsPeriod = AnalyticsPeriod.DAY,
        date_range: object = None,
    ) -> KitchenPerformance:
        assert self._kitchen is not None
        return self._kitchen


@pytest.mark.unit
async def test_get_dashboard_when_data_exists_then_returns() -> None:
    # Arrange
    repo = InMemoryAnalyticsRepository()
    expected = DashboardData(
        total_sales=Decimal("2000.00"),
        orders_count=50,
        average_ticket=Decimal("40.00"),
        low_stock_items=1,
        average_prep_time_minutes=8.0,
    )
    repo._dashboard = expected  # noqa: SLF001
    handler = GetDashboardHandler(repo)
    query = GetDashboardQuery(tenant_id="t1")

    # Act
    result = await handler.handle(query)

    # Assert
    assert result == expected
    assert result.orders_count == 50


@pytest.mark.unit
async def test_get_sales_report_when_data_exists_then_returns() -> None:
    # Arrange
    repo = InMemoryAnalyticsRepository()
    expected = SalesReportData(
        period=AnalyticsPeriod.MONTH,
        total_sales=Decimal("30000.00"),
        total_orders=800,
        average_ticket=Decimal("37.50"),
        by_category={"BEBIDAS": Decimal("10000.00")},
    )
    repo._sales = expected  # noqa: SLF001
    handler = GetSalesReportHandler(repo)
    query = GetSalesReportQuery(tenant_id="t1", period=AnalyticsPeriod.MONTH)

    # Act
    result = await handler.handle(query)

    # Assert
    assert result == expected
    assert result.total_orders == 800


@pytest.mark.unit
async def test_get_order_insights_when_data_exists_then_returns() -> None:
    # Arrange
    repo = InMemoryAnalyticsRepository()
    expected = OrderInsights(
        period=AnalyticsPeriod.WEEK,
        total_orders=350,
        average_items_per_order=2.4,
        peak_hour=19,
    )
    repo._orders = expected  # noqa: SLF001
    handler = GetOrderInsightsHandler(repo)
    query = GetOrderInsightsQuery(tenant_id="t1", period=AnalyticsPeriod.WEEK)

    # Act
    result = await handler.handle(query)

    # Assert
    assert result == expected
    assert result.peak_hour == 19


@pytest.mark.unit
async def test_get_kitchen_performance_when_data_exists_then_returns() -> None:
    # Arrange
    repo = InMemoryAnalyticsRepository()
    expected = KitchenPerformance(
        period=AnalyticsPeriod.DAY,
        average_prep_time_minutes=8.5,
        items_prepared=200,
        completion_rate=0.95,
    )
    repo._kitchen = expected  # noqa: SLF001
    handler = GetKitchenPerformanceHandler(repo)
    query = GetKitchenPerformanceQuery(tenant_id="t1")

    # Act
    result = await handler.handle(query)

    # Assert
    assert result == expected
    assert result.items_prepared == 200
