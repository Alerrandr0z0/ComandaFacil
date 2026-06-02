from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final, Protocol, runtime_checkable


@runtime_checkable
class StockItemReadRepository(Protocol):
    async def find_by_id(self, stock_item_id: int, tenant_id: str, /) -> Any | None: ...
    async def find_all(self, tenant_id: str, /) -> list[Any]: ...
    async def find_low_stock(self, tenant_id: str, /) -> list[Any]: ...


@dataclass(frozen=True)
class GetStockItemQuery:
    stock_item_id: int
    tenant_id: str


class GetStockItemHandler:
    def __init__(self, read_repo: StockItemReadRepository) -> None:
        self._read_repo: Final[StockItemReadRepository] = read_repo

    async def handle(self, query: GetStockItemQuery) -> dict[str, Any] | None:
        return await self._read_repo.find_by_id(query.stock_item_id, query.tenant_id)


@dataclass(frozen=True)
class ListStockItemsQuery:
    tenant_id: str
    low_stock_only: bool = False


class ListStockItemsHandler:
    def __init__(self, read_repo: StockItemReadRepository) -> None:
        self._read_repo: Final[StockItemReadRepository] = read_repo

    async def handle(self, query: ListStockItemsQuery) -> list[dict[str, Any]]:
        if query.low_stock_only:
            return await self._read_repo.find_low_stock(query.tenant_id)
        return await self._read_repo.find_all(query.tenant_id)
