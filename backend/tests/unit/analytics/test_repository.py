from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any

import pytest

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
        self.dashboard: DashboardData | None = None
        self.sales: SalesReportData | None = None
        self.orders: OrderInsights | None = None
        self.kitchen: KitchenPerformance | None = None

    async def get_dashboard(
        self,
        tenant_id: str,
        period: AnalyticsPeriod = AnalyticsPeriod.DAY,
        date_range: DateRange | None = None,
    ) -> DashboardData:
        assert self.dashboard is not None
        return self.dashboard

    async def get_sales_report(
        self,
        tenant_id: str,
        period: AnalyticsPeriod = AnalyticsPeriod.DAY,
        date_range: DateRange | None = None,
    ) -> SalesReportData:
        assert self.sales is not None
        return self.sales

    async def get_order_insights(
        self,
        tenant_id: str,
        period: AnalyticsPeriod = AnalyticsPeriod.DAY,
        date_range: DateRange | None = None,
    ) -> OrderInsights:
        assert self.orders is not None
        return self.orders

    async def get_kitchen_performance(
        self,
        tenant_id: str,
        period: AnalyticsPeriod = AnalyticsPeriod.DAY,
        date_range: DateRange | None = None,
    ) -> KitchenPerformance:
        assert self.kitchen is not None
        return self.kitchen

    async def get_menu_items_sales(
        self,
        tenant_id: str,
        period: AnalyticsPeriod = AnalyticsPeriod.DAY,
        date_range: DateRange | None = None,
    ) -> list[dict[str, Any]]:
        return []


def _dashboard() -> DashboardData:
    return DashboardData(
        total_sales=Decimal("1000.00"),
        orders_count=30,
        average_ticket=Decimal("33.33"),
        low_stock_items=2,
        average_prep_time_minutes=10.0,
    )


def _sales_report() -> SalesReportData:
    return SalesReportData(
        period=AnalyticsPeriod.WEEK,
        total_sales=Decimal("5000.00"),
        total_orders=120,
        average_ticket=Decimal("41.67"),
        by_category={"BEBIDAS": Decimal("2000.00")},
    )


def _order_insights() -> OrderInsights:
    return OrderInsights(
        period=AnalyticsPeriod.WEEK,
        total_orders=350,
        average_items_per_order=2.4,
        peak_hour=19,
    )


def _kitchen_performance() -> KitchenPerformance:
    return KitchenPerformance(
        period=AnalyticsPeriod.DAY,
        average_prep_time_minutes=8.5,
        average_queue_time_minutes=4.0,
        items_prepared=200,
        completion_rate=0.95,
    )


# ─── Protocol conformance ────────────────────────────────────────────────────


@pytest.mark.unit
async def test_analytics_repository_when_protocol_then_is_runtime_checkable() -> None:
    assert isinstance(InMemoryAnalyticsRepository(), AnalyticsRepository)


# ─── Contract: all 4 methods ─────────────────────────────────────────────────


@pytest.mark.unit
async def test_repository_get_dashboard_when_data_exists_then_returns() -> None:
    repo = InMemoryAnalyticsRepository()
    expected = _dashboard()
    repo.dashboard = expected

    result = await repo.get_dashboard(tenant_id="t1")

    assert result == expected
    assert result.total_sales == Decimal("1000.00")


@pytest.mark.unit
async def test_repository_get_sales_report_when_data_exists_then_returns() -> None:
    repo = InMemoryAnalyticsRepository()
    expected = _sales_report()
    repo.sales = expected

    result = await repo.get_sales_report(tenant_id="t1", period=AnalyticsPeriod.WEEK)

    assert result == expected
    assert result.total_orders == 120


@pytest.mark.unit
async def test_repository_get_order_insights_when_data_exists_then_returns() -> None:
    repo = InMemoryAnalyticsRepository()
    expected = _order_insights()
    repo.orders = expected

    result = await repo.get_order_insights(tenant_id="t1", period=AnalyticsPeriod.WEEK)

    assert result == expected
    assert result.peak_hour == 19


@pytest.mark.unit
async def test_repository_get_kitchen_performance_when_data_exists_then_returns() -> None:
    repo = InMemoryAnalyticsRepository()
    expected = _kitchen_performance()
    repo.kitchen = expected

    result = await repo.get_kitchen_performance(tenant_id="t1")

    assert result == expected
    assert result.items_prepared == 200


# ─── Param passthrough ───────────────────────────────────────────────────────


class PassthroughTracker(AnalyticsRepository):
    def __init__(self) -> None:
        self.captured: list[dict[str, Any]] = []

    async def get_dashboard(
        self,
        tenant_id: str,
        period: AnalyticsPeriod = AnalyticsPeriod.DAY,
        date_range: DateRange | None = None,
    ) -> DashboardData:
        self.captured.append(
            {
                "method": "dashboard",
                "tenant_id": tenant_id,
                "period": period,
                "date_range": date_range,
            }
        )
        return _dashboard()

    async def get_sales_report(
        self,
        tenant_id: str,
        period: AnalyticsPeriod = AnalyticsPeriod.DAY,
        date_range: DateRange | None = None,
    ) -> SalesReportData:
        self.captured.append(
            {"method": "sales", "tenant_id": tenant_id, "period": period, "date_range": date_range}
        )
        return _sales_report()

    async def get_order_insights(
        self,
        tenant_id: str,
        period: AnalyticsPeriod = AnalyticsPeriod.DAY,
        date_range: DateRange | None = None,
    ) -> OrderInsights:
        self.captured.append(
            {"method": "orders", "tenant_id": tenant_id, "period": period, "date_range": date_range}
        )
        return _order_insights()

    async def get_kitchen_performance(
        self,
        tenant_id: str,
        period: AnalyticsPeriod = AnalyticsPeriod.DAY,
        date_range: DateRange | None = None,
    ) -> KitchenPerformance:
        self.captured.append(
            {
                "method": "kitchen",
                "tenant_id": tenant_id,
                "period": period,
                "date_range": date_range,
            }
        )
        return _kitchen_performance()


@pytest.mark.unit
@pytest.mark.parametrize(
    ("method", "kwargs"),
    [
        ("get_dashboard", {"tenant_id": "t1"}),
        ("get_sales_report", {"tenant_id": "t1", "period": AnalyticsPeriod.MONTH}),
        ("get_order_insights", {"tenant_id": "t1", "period": AnalyticsPeriod.WEEK}),
        ("get_kitchen_performance", {"tenant_id": "t1"}),
    ],
)
async def test_repository_when_called_then_returns_proper_type(
    method: str, kwargs: dict[str, Any]
) -> None:
    repo = InMemoryAnalyticsRepository()
    repo.dashboard = _dashboard()
    repo.sales = _sales_report()
    repo.orders = _order_insights()
    repo.kitchen = _kitchen_performance()

    result = await getattr(repo, method)(**kwargs)

    assert result is not None


@pytest.mark.unit
async def test_repository_when_date_range_passed_then_ignored_by_stub() -> None:
    repo = InMemoryAnalyticsRepository()
    repo.dashboard = _dashboard()

    result = await repo.get_dashboard(
        tenant_id="t1",
        date_range=DateRange(
            start=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
            end=datetime.datetime(2026, 1, 31, tzinfo=datetime.UTC),
        ),
    )

    assert result.total_sales == Decimal("1000.00")
