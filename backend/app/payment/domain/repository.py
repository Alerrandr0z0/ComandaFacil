from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from app.payment.domain.payment import Payment


@runtime_checkable
class PaymentRepository(Protocol):
    """Protocol for Payment aggregate root repository."""

    async def find_by_id(self, id: int, tenant_id: str) -> Payment | None:
        """Finds a Payment transaction by its unique ID and tenant ID."""
        ...

    async def find_by_order(self, order_id: int, tenant_id: str) -> Payment | None:
        """Finds a Payment transaction linked to a specific Order ID under a tenant."""
        ...

    async def save(self, payment: Payment) -> None:
        """Persists or updates a Payment aggregate root."""
        ...
