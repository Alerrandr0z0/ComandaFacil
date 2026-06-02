from __future__ import annotations

from typing import Final, Protocol, runtime_checkable

from app.shared.exceptions import InsufficientStockError
from app.shared.value_objects import MeasuredQuantity


class StockItem:
    """Aggregate Root representing a tracked inventory item."""

    def __init__(
        self,
        id: int,
        tenant_id: str,
        name: str,
        category: str,
        current_quantity: MeasuredQuantity,
        min_stock_level: float = 0,
        is_active: bool = True,
    ) -> None:
        self.id: Final[int] = id
        self.tenant_id: Final[str] = tenant_id
        self.name: str = name
        self.category: str = category
        self.current_quantity: MeasuredQuantity = current_quantity
        self.min_stock_level: float = min_stock_level
        self.is_active: bool = is_active

    def add_stock(self, quantity: float) -> None:
        """Adds inbound stock. Quantity must be positive."""
        if quantity <= 0:
            raise ValueError(f"Quantity to add must be positive, got: {quantity}")
        new_amount = self.current_quantity.amount + quantity
        self.current_quantity = MeasuredQuantity(new_amount, self.current_quantity.unit)

    def deduct_stock(self, quantity: float) -> None:
        """Deducts stock. Raises InsufficientStockError if below zero."""
        if quantity <= 0:
            raise ValueError(f"Quantity to deduct must be positive, got: {quantity}")
        if self.current_quantity.amount < quantity:
            raise InsufficientStockError(self.name, self.current_quantity.amount, quantity)
        new_amount = self.current_quantity.amount - quantity
        self.current_quantity = MeasuredQuantity(new_amount, self.current_quantity.unit)

    def adjust_stock(self, new_quantity: float) -> None:
        """Sets stock to an absolute quantity (physical count adjustment)."""
        if new_quantity < 0:
            raise ValueError(f"Quantity cannot be negative, got: {new_quantity}")
        self.current_quantity = MeasuredQuantity(new_quantity, self.current_quantity.unit)

    def set_min_stock_level(self, level: float) -> None:
        if level < 0:
            raise ValueError(f"Minimum stock level cannot be negative, got: {level}")
        self.min_stock_level = level

    @property
    def is_low_stock(self) -> bool:
        return self.current_quantity.amount < self.min_stock_level

    def activate(self) -> None:
        self.is_active = True

    def deactivate(self) -> None:
        self.is_active = False

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(id={self.id}, name={self.name!r}, "
            f"qty={self.current_quantity}, min={self.min_stock_level}, "
            f"active={self.is_active})"
        )


@runtime_checkable
class StockItemRepository(Protocol):
    async def find_by_id(self, id: int, tenant_id: str) -> StockItem | None: ...
    async def find_by_name(self, name: str, tenant_id: str) -> StockItem | None: ...
    async def find_all(self, tenant_id: str) -> list[StockItem]: ...
    async def find_low_stock(self, tenant_id: str) -> list[StockItem]: ...
    async def save(self, item: StockItem) -> None: ...
    async def delete(self, id: int, tenant_id: str) -> None: ...
