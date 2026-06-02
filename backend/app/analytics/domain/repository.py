from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from app.analytics.domain.enums import AnalyticsPeriod

if TYPE_CHECKING:
    from app.analytics.domain.value_objects import (
        DashboardData,
        DateRange,
        KitchenPerformance,
        OrderInsights,
        SalesReportData,
    )


@runtime_checkable
class AnalyticsRepository(Protocol):
    async def get_dashboard(
        self,
        tenant_id: str,
        period: AnalyticsPeriod = AnalyticsPeriod.DAY,
        date_range: DateRange | None = None,
    ) -> DashboardData: ...

    async def get_sales_report(
        self,
        tenant_id: str,
        period: AnalyticsPeriod = AnalyticsPeriod.DAY,
        date_range: DateRange | None = None,
    ) -> SalesReportData: ...

    async def get_order_insights(
        self,
        tenant_id: str,
        period: AnalyticsPeriod = AnalyticsPeriod.DAY,
        date_range: DateRange | None = None,
    ) -> OrderInsights: ...

    async def get_kitchen_performance(
        self,
        tenant_id: str,
        period: AnalyticsPeriod = AnalyticsPeriod.DAY,
        date_range: DateRange | None = None,
    ) -> KitchenPerformance: ...
