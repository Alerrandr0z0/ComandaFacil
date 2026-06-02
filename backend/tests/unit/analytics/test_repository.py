from __future__ import annotations

from decimal import Decimal

import pytest

from typing import Optional

from app.analytics.domain.enums import AnalyticsPeriod
from app.analytics.domain.repository import AnalyticsRepository
from app.analytics.domain.value_objects import (
    DashboardData,
    DateRange,
    KitchenPerformance,
    OrderInsights,
    SalesReportData,
)


class InMemoryAnalyticsRepository(AnalyticsRepository):
    def __init__(self) -> None:
        self._dashboard: DashboardData | None = None
        self._sales: SalesReportData | None = None
        self._orders: OrderInsights | None = None
        self._kitchen: KitchenPerformance | None = None

    async def get_dashboard(
        self,
        tenant_id: str,
        period: AnalyticsPeriod = AnalyticsPeriod.DAY,
        date_range: Optional[DateRange] = None,
    ) -> DashboardData:
        assert self._dashboard is not None
        return self._dashboard

    async def get_sales_report(
        self,
        tenant_id: str,
        period: AnalyticsPeriod = AnalyticsPeriod.DAY,
        date_range: Optional[DateRange] = None,
    ) -> SalesReportData:
        assert self._sales is not None
        return self._sales

    async def get_order_insights(
        self,
        tenant_id: str,
        period: AnalyticsPeriod = AnalyticsPeriod.DAY,
        date_range: Optional[DateRange] = None,
    ) -> OrderInsights:
        assert self._orders is not None
        return self._orders

    async def get_kitchen_performance(
        self,
        tenant_id: str,
        period: AnalyticsPeriod = AnalyticsPeriod.DAY,
        date_range: Optional[DateRange] = None,
    ) -> KitchenPerformance:
        assert self._kitchen is not None
        return self._kitchen


@pytest.mark.unit
async def test_analytics_repository_when_protocol_then_is_runtime_checkable() -> None:
    # Arrange
    repo = InMemoryAnalyticsRepository()

    # Assert
    assert isinstance(repo, AnalyticsRepository)


@pytest.mark.unit
async def test_repository_get_dashboard_when_data_exists_then_returns() -> None:
    # Arrange
    repo = InMemoryAnalyticsRepository()
    expected = DashboardData(
        total_sales=Decimal("1000.00"),
        orders_count=30,
        average_ticket=Decimal("33.33"),
        low_stock_items=2,
        average_prep_time_minutes=10.0,
    )
    repo._dashboard = expected  # noqa: SLF001

    # Act
    result = await repo.get_dashboard(tenant_id="t1")

    # Assert
    assert result == expected
    assert result.total_sales == Decimal("1000.00")


@pytest.mark.unit
async def test_repository_get_sales_report_when_data_exists_then_returns() -> None:
    # Arrange
    repo = InMemoryAnalyticsRepository()
    expected = SalesReportData(
        period=AnalyticsPeriod.WEEK,
        total_sales=Decimal("5000.00"),
        total_orders=120,
        average_ticket=Decimal("41.67"),
        by_category={"BEBIDAS": Decimal("2000.00")},
    )
    repo._sales = expected  # noqa: SLF001

    # Act
    result = await repo.get_sales_report(tenant_id="t1", period=AnalyticsPeriod.WEEK)

    # Assert
    assert result == expected
    assert result.total_orders == 120
