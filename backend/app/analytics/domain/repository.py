from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from app.analytics.domain.enums import AnalyticsPeriod
from app.analytics.domain.value_objects import (
    DashboardData,
    KitchenPerformance,
    OrderInsights,
    SalesReportData,
    DateRange,
)


@runtime_checkable
class AnalyticsRepository(Protocol):
    async def get_dashboard(
        self,
        tenant_id: str,
        period: AnalyticsPeriod = AnalyticsPeriod.DAY,
        date_range: Optional[DateRange] = None,
    ) -> DashboardData:
        ...

    async def get_sales_report(
        self,
        tenant_id: str,
        period: AnalyticsPeriod = AnalyticsPeriod.DAY,
        date_range: Optional[DateRange] = None,
    ) -> SalesReportData:
        ...

    async def get_order_insights(
        self,
        tenant_id: str,
        period: AnalyticsPeriod = AnalyticsPeriod.DAY,
        date_range: Optional[DateRange] = None,
    ) -> OrderInsights:
        ...

    async def get_kitchen_performance(
        self,
        tenant_id: str,
        period: AnalyticsPeriod = AnalyticsPeriod.DAY,
        date_range: Optional[DateRange] = None,
    ) -> KitchenPerformance:
        ...
