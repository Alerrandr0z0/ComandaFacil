from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

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
    from app.stock.domain.recipe import RecipeRepository


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


@dataclass(frozen=True)
class GetMenuMatrixQuery:
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


class GetMenuMatrixHandler:
    def __init__(self, analytics_repo: AnalyticsRepository, recipe_repo: RecipeRepository) -> None:
        self._analytics_repo = analytics_repo
        self._recipe_repo = recipe_repo

    async def handle(self, query: GetMenuMatrixQuery) -> dict[str, Any]:
        sales = await self._analytics_repo.get_menu_items_sales(
            tenant_id=query.tenant_id,
            period=query.period,
            date_range=query.date_range,
        )

        items: list[dict[str, Any]] = []
        for s in sales:
            menu_item_id = s["_id"]
            name = s["name"]
            qty = s["quantity"]
            rev = s["revenue"]
            avg_p = float(rev / qty) if qty > 0 else 0.0

            # Find recipe
            recipe = await self._recipe_repo.find_by_menu_item(menu_item_id, query.tenant_id)
            cost = recipe.calculate_total_cost() if recipe else 0.0
            margin = avg_p - cost

            items.append(
                {
                    "menu_item_id": menu_item_id,
                    "name": name,
                    "quantity": qty,
                    "revenue": float(rev),
                    "avg_price": avg_p,
                    "cost": cost,
                    "margin": margin,
                }
            )

        # Calculate averages for classification
        total_items = len(items)
        avg_qty = sum(item["quantity"] for item in items) / total_items if total_items > 0 else 0.0
        avg_margin = sum(item["margin"] for item in items) / total_items if total_items > 0 else 0.0

        for item in items:
            pop = "HIGH" if item["quantity"] >= avg_qty else "LOW"
            prof = "HIGH" if item["margin"] >= avg_margin else "LOW"

            if pop == "HIGH" and prof == "HIGH":
                classif = "STAR"
                recom = (
                    "Manter e Destacar: treinar equipe para sugerir e manter a receita idêntica."
                )
            elif pop == "LOW" and prof == "HIGH":
                classif = "PUZZLE"
                recom = "Promover: reduzir preço levemente ou destacar visibilidade no cardápio."
            elif pop == "HIGH" and prof == "LOW":
                classif = "PLOWHORSE"
                recom = "Reengenharia de Custos: renegociar insumos ou ajustar preço para elevar margem."
            else:
                classif = "DOG"
                recom = "Substituir ou Reformular: remover do cardápio ou reformular com novos ingredientes."

            item["popularity"] = pop
            item["profitability"] = prof
            item["classification"] = classif
            item["recommendation"] = recom

        return {
            "items": items,
            "average_quantity": avg_qty,
            "average_margin": avg_margin,
        }
