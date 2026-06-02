from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from app.shared.exceptions import NotFoundError

if TYPE_CHECKING:
    from app.stock.domain.stock_item import StockItem, StockItemRepository


@dataclass(frozen=True)
class GetStockItemQuery:
    stock_item_id: int
    tenant_id: str


class GetStockItemHandler:
    def __init__(self, repo: StockItemRepository) -> None:
        self._repo: Final[StockItemRepository] = repo

    async def handle(self, query: GetStockItemQuery) -> StockItem:
        item = await self._repo.find_by_id(query.stock_item_id, query.tenant_id)
        if not item:
            raise NotFoundError("StockItem", query.stock_item_id)
        return item


@dataclass(frozen=True)
class ListStockItemsQuery:
    tenant_id: str
    low_stock_only: bool = False


class ListStockItemsHandler:
    def __init__(self, repo: StockItemRepository) -> None:
        self._repo: Final[StockItemRepository] = repo

    async def handle(self, query: ListStockItemsQuery) -> list[StockItem]:
        if query.low_stock_only:
            return await self._repo.find_low_stock(query.tenant_id)
        return await self._repo.find_all(query.tenant_id)
