from __future__ import annotations

import datetime
from decimal import Decimal

import pytest

from app.analytics.domain.enums import AnalyticsPeriod
from app.analytics.domain.value_objects import DashboardData, DateRange


def test_analytics_period_when_day_then_has_correct_values() -> None:
    # Arrange
    period = AnalyticsPeriod.DAY

    # Assert
    assert period.value == "day"


def test_date_range_when_valid_dates_then_creates() -> None:
    # Arrange
    start = datetime.datetime(2026, 6, 1, tzinfo=datetime.UTC)
    end = datetime.datetime(2026, 6, 2, tzinfo=datetime.UTC)

    # Act
    dr = DateRange(start=start, end=end)

    # Assert
    assert dr.start == start
    assert dr.end == end


def test_date_range_when_end_before_start_then_raises() -> None:
    # Arrange
    start = datetime.datetime(2026, 6, 2, tzinfo=datetime.UTC)
    end = datetime.datetime(2026, 6, 1, tzinfo=datetime.UTC)

    # Act & Assert
    with pytest.raises(ValueError, match="end must be after or equal to start"):
        DateRange(start=start, end=end)


def test_dashboard_data_when_valid_then_creates() -> None:
    # Arrange
    data = DashboardData(
        total_sales=Decimal("1250.00"),
        orders_count=42,
        average_ticket=Decimal("29.76"),
        low_stock_items=3,
        average_prep_time_minutes=12.5,
    )

    # Assert
    assert data.total_sales == Decimal("1250.00")
    assert data.orders_count == 42
    assert data.average_ticket == Decimal("29.76")
    assert data.low_stock_items == 3
    assert data.average_prep_time_minutes == 12.5


def test_sales_report_data_when_valid_then_creates() -> None:
    from app.analytics.domain.value_objects import SalesReportData

    # Arrange
    report = SalesReportData(
        period=AnalyticsPeriod.DAY,
        total_sales=Decimal("5000.00"),
        total_orders=120,
        average_ticket=Decimal("41.67"),
        by_category={"BEBIDAS": Decimal("1500.00"), "PRATOS": Decimal("3500.00")},
    )

    # Assert
    assert report.period == AnalyticsPeriod.DAY
    assert report.total_sales == Decimal("5000.00")
    assert report.total_orders == 120
    assert report.average_ticket == Decimal("41.67")
    assert report.by_category == {"BEBIDAS": Decimal("1500.00"), "PRATOS": Decimal("3500.00")}


def test_order_insights_when_valid_then_creates() -> None:
    from app.analytics.domain.value_objects import OrderInsights

    # Arrange
    insights = OrderInsights(
        period=AnalyticsPeriod.WEEK,
        total_orders=350,
        average_items_per_order=2.4,
        peak_hour=19,
    )

    # Assert
    assert insights.period == AnalyticsPeriod.WEEK
    assert insights.total_orders == 350
    assert insights.average_items_per_order == 2.4
    assert insights.peak_hour == 19


def test_kitchen_performance_when_valid_then_creates() -> None:
    from app.analytics.domain.value_objects import KitchenPerformance

    # Arrange
    perf = KitchenPerformance(
        period=AnalyticsPeriod.DAY,
        average_prep_time_minutes=8.5,
        items_prepared=200,
        completion_rate=0.95,
    )

    # Assert
    assert perf.period == AnalyticsPeriod.DAY
    assert perf.average_prep_time_minutes == 8.5
    assert perf.items_prepared == 200
    assert perf.completion_rate == 0.95
