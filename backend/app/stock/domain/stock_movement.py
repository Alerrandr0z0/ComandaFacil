from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable

from app.stock.domain.enums import MovementType


@dataclass(frozen=True)
class StockMovement:
    """Value Object recording a stock quantity change."""

    id: int
    stock_item_id: int
    movement_type: MovementType
    quantity_changed: float
    reason: str = ""
    reference_type: str | None = None
    reference_id: int | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __repr__(self) -> str:
        return (
            f"StockMovement(id={self.id}, item_id={self.stock_item_id}, "
            f"type={self.movement_type.value}, qty={self.quantity_changed})"
        )


@runtime_checkable
class StockMovementRepository(Protocol):
    async def find_by_stock_item(
        self, stock_item_id: int, tenant_id: str
    ) -> list[StockMovement]: ...
    async def save(self, movement: StockMovement) -> None: ...
