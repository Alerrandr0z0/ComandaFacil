from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.kitchen.domain.kitchen_item import KitchenOrderItem
    from app.kitchen.domain.kitchen_station import KitchenStation


class KitchenOrderItemRepository(ABC):
    """Abstract Repository interface for KitchenOrderItem aggregate root."""

    @abstractmethod
    async def find_by_id(self, id: int, tenant_id: str) -> KitchenOrderItem | None:
        """Finds a KitchenOrderItem by its unique ID scoped to a tenant."""

    @abstractmethod
    async def find_by_correlation(
        self, correlation_id: int, tenant_id: str
    ) -> KitchenOrderItem | None:
        """Finds a KitchenOrderItem by its original OrderFormItem correlation ID scoped to a tenant."""

    @abstractmethod
    async def find_by_station(self, station_type: str, tenant_id: str) -> list[KitchenOrderItem]:
        """Finds all active KitchenOrderItems destined for a specific station type and tenant."""

    @abstractmethod
    async def save(self, item: KitchenOrderItem) -> None:
        """Persists or updates a KitchenOrderItem aggregate root."""


class KitchenStationRepository(ABC):
    """Abstract Repository interface for KitchenStation aggregate root."""

    @abstractmethod
    async def find_by_type(self, tenant_id: str, station_type: str) -> list[KitchenStation]:
        """Finds all KitchenStations of a specific type under a given tenant."""

    @abstractmethod
    async def save(self, station: KitchenStation) -> None:
        """Persists or updates a KitchenStation."""
