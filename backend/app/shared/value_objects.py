import re
from dataclasses import dataclass
from enum import StrEnum


@dataclass(frozen=True)
class Email:
    """Value object for validated email addresses."""
    value: str

    def __post_init__(self) -> None:
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, self.value):
            raise ValueError(f"Email inválido: '{self.value}'")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class TableNum:
    """Value object for table numbers."""
    value: int

    def __post_init__(self) -> None:
        if self.value < 1:
            raise ValueError(f"Número de mesa inválido: {self.value}. Deve ser >= 1.")

    def __str__(self) -> str:
        return str(self.value)


class MeasurementUnit(StrEnum):
    # Metric
    GRAM = "g"
    KILOGRAM = "kg"
    MILLILITER = "ml"
    LITER = "l"
    # Imperial
    OUNCE = "oz"
    POUND = "lb"
    FLUID_OUNCE = "fl_oz"
    # Count
    UNIT = "un"


@dataclass(frozen=True)
class MeasuredQuantity:
    """Value object for physical quantities with units."""
    amount: float
    unit: MeasurementUnit

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError(f"Quantidade não pode ser negativa: {self.amount}")

    def __str__(self) -> str:
        return f"{self.amount}{self.unit.value}"
