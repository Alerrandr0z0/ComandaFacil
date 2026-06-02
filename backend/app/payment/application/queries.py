from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final, Protocol, runtime_checkable


@runtime_checkable
class PaymentReadRepository(Protocol):
    async def find_by_order(self, order_id: int, tenant_id: str, /) -> Any | None: ...
    async def find_by_id(self, payment_id: int, tenant_id: str, /) -> Any | None: ...


@dataclass(frozen=True)
class GetPaymentByOrderQuery:
    order_id: int
    tenant_id: str

    def __repr__(self) -> str:
        return f"GetPaymentByOrderQuery(order_id={self.order_id}, tenant_id={self.tenant_id!r})"


class GetPaymentByOrderHandler:
    def __init__(self, read_repo: PaymentReadRepository) -> None:
        self._read_repo: Final[PaymentReadRepository] = read_repo

    async def handle(self, query: GetPaymentByOrderQuery) -> dict[str, Any] | None:
        """Fetch a payment read model by order ID."""
        return await self._read_repo.find_by_order(query.order_id, query.tenant_id)

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"


@dataclass(frozen=True)
class GetPaymentByIdQuery:
    payment_id: int
    tenant_id: str

    def __repr__(self) -> str:
        return f"GetPaymentByIdQuery(payment_id={self.payment_id}, tenant_id={self.tenant_id!r})"


class GetPaymentByIdHandler:
    def __init__(self, read_repo: PaymentReadRepository) -> None:
        self._read_repo: Final[PaymentReadRepository] = read_repo

    async def handle(self, query: GetPaymentByIdQuery) -> dict[str, Any] | None:
        """Fetch a payment read model by payment ID."""
        return await self._read_repo.find_by_id(query.payment_id, query.tenant_id)

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"
