from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import datetime
    from decimal import Decimal

    from app.analytics.domain.enums import AnalyticsPeriod


@dataclass(frozen=True)
class DateRange:
    start: datetime.datetime
    end: datetime.datetime

    def __post_init__(self) -> None:
        if self.end < self.start:
            msg = "end must be after or equal to start"
            raise ValueError(msg)


@dataclass(frozen=True)
class DashboardData:
    total_sales: Decimal
    orders_count: int
    average_ticket: Decimal
    low_stock_items: int
    average_prep_time_minutes: float


@dataclass(frozen=True)
class SalesReportData:
    period: AnalyticsPeriod
    total_sales: Decimal
    total_orders: int
    average_ticket: Decimal
    by_category: dict[str, Decimal] = field(default_factory=dict)
    trends: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class OrderInsights:
    period: AnalyticsPeriod
    total_orders: int
    average_items_per_order: float
    peak_hour: int
    heatmap: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class KitchenPerformance:
    period: AnalyticsPeriod
    average_prep_time_minutes: float
    average_queue_time_minutes: float
    items_prepared: int
    completion_rate: float
    by_station: dict[str, dict[str, Any]] = field(default_factory=dict)
    sla_compliance_rate: float = 0.0
    bottlenecks: list[dict[str, Any]] = field(default_factory=list)
    throughput_trends: list[dict[str, Any]] = field(default_factory=list)
    std_dev_prep_time_minutes: float = 0.0
    queue_vs_prep_trends: list[dict[str, Any]] = field(default_factory=list)
    waste_cancelled_value: float = 0.0
    waste_cancelled_count: int = 0
