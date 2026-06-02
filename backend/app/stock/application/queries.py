from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from app.stock.infrastructure.mongo_read_repository import (
        MongoStockReadRepository,
    )


@dataclass(frozen=True)
class GetStockItemQuery:
    stock_item_id: int
    tenant_id: str


class GetStockItemHandler:
    def __init__(self, read_repo: MongoStockReadRepository) -> None:
        self._read_repo: Final[MongoStockReadRepository] = read_repo

    async def handle(self, query: GetStockItemQuery) -> dict[str, Any] | None:
        return await self._read_repo.find_by_id(
            query.stock_item_id, query.tenant_id
        )


@dataclass(frozen=True)
class ListStockItemsQuery:
    tenant_id: str
    low_stock_only: bool = False


class ListStockItemsHandler:
    def __init__(self, read_repo: MongoStockReadRepository) -> None:
        self._read_repo: Final[MongoStockReadRepository] = read_repo

    async def handle(self, query: ListStockItemsQuery) -> list[dict[str, Any]]:
        if query.low_stock_only:
            return await self._read_repo.find_low_stock(query.tenant_id)
        return await self._read_repo.find_all(query.tenant_id)
