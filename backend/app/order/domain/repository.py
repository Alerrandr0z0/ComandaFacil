from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.order.domain.order_form import OrderForm


class OrderRepository(ABC):
    """Abstract Repository interface for OrderForm aggregate root."""

    @abstractmethod
    async def find_by_id(self, id: int, tenant_id: str) -> OrderForm | None:
        """Finds an OrderForm by its unique ID scoped to a tenant."""

    @abstractmethod
    async def find_all_by_tenant(self, tenant_id: str) -> list[OrderForm]:
        """Finds all OrderForms belonging to a specific tenant."""

    @abstractmethod
    async def find_all_active_by_tenant(self, tenant_id: str) -> list[OrderForm]:
        """Finds all active (non-CLOSED) OrderForms belonging to a specific tenant."""

    @abstractmethod
    async def save(self, order: OrderForm) -> None:
        """Persists or updates an OrderForm aggregate root."""

    @abstractmethod
    async def delete(self, id: int, tenant_id: str) -> None:
        """Deletes an OrderForm by its ID scoped to a tenant."""
