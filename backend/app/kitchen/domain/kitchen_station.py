from __future__ import annotations

from abc import ABC, abstractmethod


class KitchenStation(ABC):
    """Abstract Base Class representing a preparation station in the kitchen (KDS)."""

    def __init__(self, id: int, tenant_id: str, is_active: bool = True) -> None:
        self.id: int = id
        self.tenant_id: str = tenant_id
        self.is_active: bool = is_active

    @property
    @abstractmethod
    def station_type(self) -> str:
        """Returns the specific type of the kitchen station."""

    def add_item(self) -> None:
        """Stub method to support Javadoc UML signature."""
        raise NotImplementedError(
            "Subclasses should implement station-specific item tracking rules."
        )

    def cancel_item(self) -> None:
        """Stub method to support Javadoc UML signature."""
        raise NotImplementedError(
            "Subclasses should implement station-specific item cancellation rules."
        )

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(id={self.id}, tenant_id={self.tenant_id!r}, "
            f"is_active={self.is_active}, station_type={self.station_type!r})"
        )


class Grill(KitchenStation):
    """Grill station for hot food preparation (burgers, hot dogs, etc.)."""

    @property
    def station_type(self) -> str:
        return "GRILL"


class Beverage(KitchenStation):
    """Beverage station for drink preparation (sodas, juices, milkshakes, etc.)."""

    @property
    def station_type(self) -> str:
        return "BEVERAGE"
