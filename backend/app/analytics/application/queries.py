from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.analytics.domain.enums import AnalyticsPeriod

if TYPE_CHECKING:
    from app.analytics.domain.repository import AnalyticsRepository
    from app.analytics.domain.value_objects import (
        DashboardData,
        DateRange,
        KitchenPerformance,
        OrderInsights,
        SalesReportData,
    )


@dataclass(frozen=True)
class GetDashboardQuery:
    tenant_id: str
    period: AnalyticsPeriod = AnalyticsPeriod.DAY
    date_range: DateRange | None = None


@dataclass(frozen=True)
class GetSalesReportQuery:
    tenant_id: str
    period: AnalyticsPeriod = AnalyticsPeriod.DAY
    date_range: DateRange | None = None


@dataclass(frozen=True)
class GetOrderInsightsQuery:
    tenant_id: str
    period: AnalyticsPeriod = AnalyticsPeriod.DAY
    date_range: DateRange | None = None


@dataclass(frozen=True)
class GetKitchenPerformanceQuery:
    tenant_id: str
    period: AnalyticsPeriod = AnalyticsPeriod.DAY
    date_range: DateRange | None = None


class GetDashboardHandler:
    def __init__(self, repo: AnalyticsRepository) -> None:
        self._repo = repo

    async def handle(self, query: GetDashboardQuery) -> DashboardData:
        return await self._repo.get_dashboard(
            tenant_id=query.tenant_id,
            period=query.period,
            date_range=query.date_range,
        )


class GetSalesReportHandler:
    def __init__(self, repo: AnalyticsRepository) -> None:
        self._repo = repo

    async def handle(self, query: GetSalesReportQuery) -> SalesReportData:
        return await self._repo.get_sales_report(
            tenant_id=query.tenant_id,
            period=query.period,
            date_range=query.date_range,
        )


class GetOrderInsightsHandler:
    def __init__(self, repo: AnalyticsRepository) -> None:
        self._repo = repo

    async def handle(self, query: GetOrderInsightsQuery) -> OrderInsights:
        return await self._repo.get_order_insights(
            tenant_id=query.tenant_id,
            period=query.period,
            date_range=query.date_range,
        )


class GetKitchenPerformanceHandler:
    def __init__(self, repo: AnalyticsRepository) -> None:
        self._repo = repo

    async def handle(self, query: GetKitchenPerformanceQuery) -> KitchenPerformance:
        return await self._repo.get_kitchen_performance(
            tenant_id=query.tenant_id,
            period=query.period,
            date_range=query.date_range,
        )
