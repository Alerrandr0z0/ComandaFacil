from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.analytics.domain.enums import AnalyticsPeriod
from app.analytics.domain.value_objects import (
    DashboardData,
    DateRange,
    KitchenPerformance,
    OrderInsights,
    SalesReportData,
)

# ─── Hypothesis strategies ─────────────────────────────────────────────────────

naive_dt = st.datetimes(
    min_value=datetime.datetime(2000, 1, 1),
    max_value=datetime.datetime(2099, 12, 31),
)
aware_dt = st.datetimes(timezones=st.timezones()).filter(
    lambda dt: (
        datetime.datetime(2000, 1, 1, tzinfo=datetime.UTC)
        <= dt
        <= datetime.datetime(2099, 12, 31, tzinfo=datetime.UTC)
    )
)

non_neg_decimals = st.decimals(
    min_value=Decimal("0"),
    max_value=Decimal("999999999.99"),
    allow_nan=False,
    allow_infinity=False,
    places=2,
)
positive_decimals = st.decimals(
    min_value=Decimal("0.01"),
    max_value=Decimal("999999999.99"),
    allow_nan=False,
    allow_infinity=False,
    places=2,
)
positive_ints = st.integers(min_value=0, max_value=999999)
small_positive_ints = st.integers(min_value=0, max_value=10000)
non_neg_floats = st.floats(
    min_value=0.0,
    max_value=1e9,
    allow_nan=False,
    allow_infinity=False,
)
rate_floats = st.floats(
    min_value=0.0,
    max_value=1.0,
    allow_nan=False,
    allow_infinity=False,
)
hour_ints = st.integers(min_value=0, max_value=23)
periods = st.sampled_from(list(AnalyticsPeriod))
categories = st.dictionaries(
    keys=st.text(min_size=1, max_size=20),
    values=non_neg_decimals,
    min_size=0,
    max_size=10,
)


# ─── AnalyticsPeriod ──────────────────────────────────────────────────────────


def test_analytics_period_when_day_then_has_correct_values() -> None:
    assert AnalyticsPeriod.DAY.value == "day"


@given(periods)
def test_analytics_period_when_any_then_has_value(period: AnalyticsPeriod) -> None:
    assert isinstance(period.value, str)
    assert period.value in {"day", "week", "month", "custom"}


@given(periods)
def test_analytics_period_when_any_then_unique(period: AnalyticsPeriod) -> None:
    assert len({p.value for p in AnalyticsPeriod}) == 4


# ─── DateRange ────────────────────────────────────────────────────────────────


def test_date_range_when_valid_dates_then_creates() -> None:
    start = datetime.datetime(2026, 6, 1, tzinfo=datetime.UTC)
    end = datetime.datetime(2026, 6, 2, tzinfo=datetime.UTC)
    dr = DateRange(start=start, end=end)
    assert dr.start == start
    assert dr.end == end


def test_date_range_when_end_before_start_then_raises() -> None:
    start = datetime.datetime(2026, 6, 2, tzinfo=datetime.UTC)
    end = datetime.datetime(2026, 6, 1, tzinfo=datetime.UTC)
    with pytest.raises(ValueError, match="end must be after or equal to start"):
        DateRange(start=start, end=end)


@given(naive_dt, naive_dt)
def test_date_range_pbt_when_start_before_end_then_created(
    a: datetime.datetime, b: datetime.datetime
) -> None:
    start = min(a, b)
    end = max(a, b)
    dr = DateRange(start=start, end=end)
    assert dr.start == start
    assert dr.end == end


@given(naive_dt)
def test_date_range_pbt_when_equal_then_created(dt: datetime.datetime) -> None:
    dr = DateRange(start=dt, end=dt)
    assert dr.start == dr.end


@given(naive_dt, naive_dt)
def test_date_range_pbt_when_end_before_start_then_error(
    a: datetime.datetime, b: datetime.datetime
) -> None:
    start = max(a, b)
    end = min(a, b)
    if end >= start:
        return
    with pytest.raises(ValueError, match="end must be after or equal to start"):
        DateRange(start=start, end=end)


# ─── DashboardData ────────────────────────────────────────────────────────────


@given(
    total_sales=non_neg_decimals,
    orders_count=small_positive_ints,
    average_ticket=non_neg_decimals,
    low_stock_items=small_positive_ints,
    average_prep_time_minutes=non_neg_floats,
)
def test_dashboard_data_hypothesis_when_valid_fields_then_creates(
    total_sales: Decimal,
    orders_count: int,
    average_ticket: Decimal,
    low_stock_items: int,
    average_prep_time_minutes: float,
) -> None:
    data = DashboardData(
        total_sales=total_sales,
        orders_count=orders_count,
        average_ticket=average_ticket,
        low_stock_items=low_stock_items,
        average_prep_time_minutes=average_prep_time_minutes,
    )
    assert data.total_sales == total_sales
    assert data.orders_count == orders_count
    assert data.average_ticket == average_ticket
    assert data.low_stock_items == low_stock_items
    assert data.average_prep_time_minutes == average_prep_time_minutes


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("orders_count", -1),
        ("low_stock_items", -1),
        ("average_prep_time_minutes", -1.0),
    ],
)
def test_dashboard_data_when_negative_then_creates_anyway(
    field: str,
    value: int | float,
) -> None:
    kwargs = {
        "total_sales": Decimal("100"),
        "orders_count": 1,
        "average_ticket": Decimal("10"),
        "low_stock_items": 0,
        "average_prep_time_minutes": 0.0,
    }
    kwargs[field] = value
    data = DashboardData(**kwargs)  # type: ignore[arg-type]
    assert getattr(data, field) == value


# ─── SalesReportData ──────────────────────────────────────────────────────────


@given(
    period=periods,
    total_sales=non_neg_decimals,
    total_orders=small_positive_ints,
    average_ticket=non_neg_decimals,
    by_category=categories,
)
def test_sales_report_data_hypothesis_when_valid_then_creates(
    period: AnalyticsPeriod,
    total_sales: Decimal,
    total_orders: int,
    average_ticket: Decimal,
    by_category: dict[str, Decimal],
) -> None:
    report = SalesReportData(
        period=period,
        total_sales=total_sales,
        total_orders=total_orders,
        average_ticket=average_ticket,
        by_category=by_category,
    )
    assert report.period == period
    assert report.total_sales == total_sales
    assert report.total_orders == total_orders
    assert report.average_ticket == average_ticket
    assert report.by_category == by_category


def test_sales_report_data_when_empty_category_then_default() -> None:
    report = SalesReportData(
        period=AnalyticsPeriod.DAY,
        total_sales=Decimal("0"),
        total_orders=0,
        average_ticket=Decimal("0"),
    )
    assert report.by_category == {}


# ─── OrderInsights ────────────────────────────────────────────────────────────


@given(
    period=periods,
    total_orders=small_positive_ints,
    average_items_per_order=non_neg_floats,
    peak_hour=hour_ints,
)
def test_order_insights_hypothesis_when_valid_then_creates(
    period: AnalyticsPeriod,
    total_orders: int,
    average_items_per_order: float,
    peak_hour: int,
) -> None:
    insights = OrderInsights(
        period=period,
        total_orders=total_orders,
        average_items_per_order=average_items_per_order,
        peak_hour=peak_hour,
    )
    assert insights.period == period
    assert insights.total_orders == total_orders
    assert insights.average_items_per_order == average_items_per_order
    assert insights.peak_hour == peak_hour


def test_order_insights_when_peak_hour_boundary_low() -> None:
    insights = OrderInsights(
        period=AnalyticsPeriod.DAY, total_orders=0, average_items_per_order=0.0, peak_hour=0
    )
    assert insights.peak_hour == 0


def test_order_insights_when_peak_hour_boundary_high() -> None:
    insights = OrderInsights(
        period=AnalyticsPeriod.DAY, total_orders=0, average_items_per_order=0.0, peak_hour=23
    )
    assert insights.peak_hour == 23


# ─── KitchenPerformance ───────────────────────────────────────────────────────


@given(
    period=periods,
    average_prep_time_minutes=non_neg_floats,
    items_prepared=small_positive_ints,
    completion_rate=rate_floats,
)
def test_kitchen_performance_hypothesis_when_valid_then_creates(
    period: AnalyticsPeriod,
    average_prep_time_minutes: float,
    items_prepared: int,
    completion_rate: float,
) -> None:
    perf = KitchenPerformance(
        period=period,
        average_prep_time_minutes=average_prep_time_minutes,
        items_prepared=items_prepared,
        completion_rate=completion_rate,
    )
    assert perf.period == period
    assert perf.average_prep_time_minutes == average_prep_time_minutes
    assert perf.items_prepared == items_prepared
    assert perf.completion_rate == completion_rate
