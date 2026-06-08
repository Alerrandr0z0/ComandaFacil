from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.stock.domain.enums import TransactionType
    from app.stock.domain.measured_quantity import MeasuredQuantity


@dataclass(frozen=True)
class StockTransaction:
    id: int
    quantity: MeasuredQuantity
    type: TransactionType
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __repr__(self) -> str:
        return f"StockTransaction(id={self.id}, type={self.type.value}, qty={self.quantity})"
