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
            # Use avg_price directly from the database query which computes from item price
            # instead of revenue / qty (which fails for 0 subtotal items)
            avg_p = s.get("avg_price", 0.0)

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
            self._classify_item(item, avg_qty, avg_margin)

        return {
            "items": items,
            "average_quantity": avg_qty,
            "average_margin": avg_margin,
        }

    def _classify_item(self, item: dict[str, Any], avg_qty: float, avg_margin: float) -> None:
        pop = "HIGH" if item["quantity"] >= avg_qty else "LOW"
        prof = "HIGH" if item["margin"] >= avg_margin else "LOW"

        if pop == "HIGH" and prof == "HIGH":
            classif = "ELITE"
            recom = "Manter e Destacar: Produto de alta performance. Treinar equipe para manter padrão de excelência."
        elif pop == "LOW" and prof == "HIGH":
            classif = "OPORTUNIDADE"
            recom = "Promover: Alta margem com baixo giro. Avaliar ações de marketing ou ajuste estratégico de preço."
        elif pop == "HIGH" and prof == "LOW":
            classif = "ALTO_VOLUME"
            recom = "Otimização de Custos: Alta demanda com baixa margem. Renegociar insumos para elevar rentabilidade."
        else:
            classif = "BAIXO_DESEMPENHO"
            recom = "Substituir ou Reformular: Baixa performance global. Avaliar exclusão ou renovação total do item."

        item["popularity"] = pop
        item["profitability"] = prof
        item["classification"] = classif
        item["recommendation"] = recom
