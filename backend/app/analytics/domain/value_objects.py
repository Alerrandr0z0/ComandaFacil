from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

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


@dataclass(frozen=True)
class OrderInsights:
    period: AnalyticsPeriod
    total_orders: int
    average_items_per_order: float
    peak_hour: int


@dataclass(frozen=True)
class KitchenPerformance:
    period: AnalyticsPeriod
    average_prep_time_minutes: float
    items_prepared: int
    completion_rate: float
