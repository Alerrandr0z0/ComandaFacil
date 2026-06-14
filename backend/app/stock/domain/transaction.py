from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from app.stock.domain.enums import TransactionType

if TYPE_CHECKING:
    from app.stock.domain.measured_quantity import MeasuredQuantity


@dataclass(frozen=True)
class StockTransaction:
    id: int
    quantity: MeasuredQuantity
    type: TransactionType
    cost_amount: Decimal = Decimal("0.0")
    reason: str = ""
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if self.type == TransactionType.INPUT and self.cost_amount <= Decimal("0.0"):
            raise ValueError(
                "Preço de custo unitário deve ser maior que zero para transações de entrada."
            )

    def __repr__(self) -> str:
        return (
            f"StockTransaction(id={self.id}, type={self.type.value}, qty={self.quantity}, "
            f"cost={self.cost_amount}, reason={self.reason!r})"
        )
