from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from app.stock.domain.converters import ImperialConverter, MetricConverter

if TYPE_CHECKING:
    from app.stock.domain.converters import UnitConverter


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

    value: Decimal
    unit: str  # unit is String in UML diagram

    def __post_init__(self) -> None:
        # Support initializing with string/float by casting to Decimal
        if not isinstance(self.value, Decimal):  # type: ignore[reportUnnecessaryIsInstance]
            object.__setattr__(self, "value", Decimal(str(self.value)))
        if self.value < Decimal("0"):
            raise ValueError(f"Quantidade não pode ser negativa: {self.value}")

    @property
    def amount(self) -> float:
        """Alias for compatibility with float-based code."""
        return float(self.value)

    def convert_to(self, unit: str, converter: UnitConverter) -> MeasuredQuantity:
        """Converts to a target unit using a converter."""
        new_val = converter.convert(self.value, self.unit, unit)
        return MeasuredQuantity(new_val, unit)

    def add(self, other: MeasuredQuantity) -> MeasuredQuantity:
        """Adds another MeasuredQuantity, converting its unit if needed."""
        if self.unit == other.unit:
            return MeasuredQuantity(self.value + other.value, self.unit)
        # Attempt metric converter first, then fallback to imperial if metric fails
        try:
            converted_val = MetricConverter().convert(other.value, other.unit, self.unit)
        except ValueError:
            converted_val = ImperialConverter().convert(other.value, other.unit, self.unit)
        return MeasuredQuantity(self.value + converted_val, self.unit)

    def subtract(self, other: MeasuredQuantity) -> MeasuredQuantity:
        """Subtracts another MeasuredQuantity, converting its unit if needed."""
        if self.unit == other.unit:
            return MeasuredQuantity(self.value - other.value, self.unit)
        try:
            converted_val = MetricConverter().convert(other.value, other.unit, self.unit)
        except ValueError:
            converted_val = ImperialConverter().convert(other.value, other.unit, self.unit)
        return MeasuredQuantity(self.value - converted_val, self.unit)

    def __str__(self) -> str:
        return f"{self.value}{self.unit}"
