from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from app.order.domain.order_form import OrderForm
    from app.order.domain.repository import OrderRepository
    from app.order.infrastructure.mongo_repository import OrderHistoryMongoRepository


@dataclass(frozen=True)
class GetOrderQuery:
    order_id: int
    tenant_id: str

    def __repr__(self) -> str:
        return f"GetOrderQuery(order_id={self.order_id}, tenant_id={self.tenant_id!r})"


class GetOrderHandler:
    def __init__(self, order_repo: OrderRepository) -> None:
        self._order_repo: Final[OrderRepository] = order_repo

    async def handle(self, query: GetOrderQuery) -> OrderForm | None:
        """Fetch active OrderForm details from relational write database."""
        return await self._order_repo.find_by_id(query.order_id, query.tenant_id)

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"


@dataclass(frozen=True)
class GetOrderHistoryQuery:
    tenant_id: str
    limit: int = 1000
    start_date: str | None = None
    end_date: str | None = None

    def __repr__(self) -> str:
        return f"GetOrderHistoryQuery(tenant_id={self.tenant_id!r}, limit={self.limit}, start_date={self.start_date!r}, end_date={self.end_date!r})"


class GetOrderHistoryHandler:
    def __init__(self, mongo_repo: OrderHistoryMongoRepository) -> None:
        self._mongo_repo: Final[OrderHistoryMongoRepository] = mongo_repo

    async def handle(self, query: GetOrderHistoryQuery) -> list[dict[str, Any]]:
        """Fetch completed order read models from NoSQL read database."""
        return await self._mongo_repo.find_all_by_tenant(
            query.tenant_id, limit=query.limit, start_date=query.start_date, end_date=query.end_date
        )

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"
