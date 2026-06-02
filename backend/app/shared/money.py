from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = "BRL"

    def __post_init__(self) -> None:
        if self.amount < Decimal("0"):
            raise ValueError(f"Valor monetário não pode ser negativo: {self.amount}")

    def __add__(self, other: Money) -> Money:
        if self.currency != other.currency:
            raise ValueError(f"Moedas incompatíveis: {self.currency} vs {other.currency}")
        return Money(self.amount + other.amount, self.currency)

    def __mul__(self, factor: int | Decimal) -> Money:
        return Money(self.amount * Decimal(str(factor)), self.currency)

    def __str__(self) -> str:
        return f"{self.currency} {self.amount:.2f}"

    @staticmethod
    def zero(currency: str = "BRL") -> Money:
        return Money(Decimal("0.00"), currency)

    @staticmethod
    def from_float(value: float, currency: str = "BRL") -> Money:
        amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return Money(amount, currency)
