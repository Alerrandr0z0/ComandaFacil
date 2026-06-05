from __future__ import annotations

from decimal import Decimal
from typing import ClassVar, Protocol


class UnitConverter(Protocol):
    def convert(self, value: Decimal, from_unit: str, to_unit: str) -> Decimal:
        """Converts value from one unit to another."""
        ...


class MetricConverter:
    # Conversion rates relative to base units: grams for mass, milliliters for volume
    MASS_UNITS: ClassVar[dict[str, Decimal]] = {
        "g": Decimal("1"),
        "kg": Decimal("1000"),
    }
    VOLUME_UNITS: ClassVar[dict[str, Decimal]] = {
        "ml": Decimal("1"),
        "l": Decimal("1000"),
    }

    def convert(self, value: Decimal, from_unit: str, to_unit: str) -> Decimal:
        from_unit = from_unit.lower()
        to_unit = to_unit.lower()

        if from_unit == to_unit:
            return value

        # Check mass units
        if from_unit in self.MASS_UNITS and to_unit in self.MASS_UNITS:
            base_value = value * self.MASS_UNITS[from_unit]
            return base_value / self.MASS_UNITS[to_unit]

        # Check volume units
        if from_unit in self.VOLUME_UNITS and to_unit in self.VOLUME_UNITS:
            base_value = value * self.VOLUME_UNITS[from_unit]
            return base_value / self.VOLUME_UNITS[to_unit]

        raise ValueError(f"Cannot convert between {from_unit} and {to_unit} using MetricConverter")


class ImperialConverter:
    # Conversion rates relative to base units: ounce for mass, fluid ounce for volume
    MASS_UNITS: ClassVar[dict[str, Decimal]] = {
        "oz": Decimal("1"),
        "lb": Decimal("16"),
    }
    VOLUME_UNITS: ClassVar[dict[str, Decimal]] = {
        "fl_oz": Decimal("1"),
    }

    def convert(self, value: Decimal, from_unit: str, to_unit: str) -> Decimal:
        from_unit = from_unit.lower()
        to_unit = to_unit.lower()

        if from_unit == to_unit:
            return value

        # Check mass units
        if from_unit in self.MASS_UNITS and to_unit in self.MASS_UNITS:
            base_value = value * self.MASS_UNITS[from_unit]
            return base_value / self.MASS_UNITS[to_unit]

        # Check volume units
        if from_unit in self.VOLUME_UNITS and to_unit in self.VOLUME_UNITS:
            base_value = value * self.VOLUME_UNITS[from_unit]
            return base_value / self.VOLUME_UNITS[to_unit]

        raise ValueError(
            f"Cannot convert between {from_unit} and {to_unit} using ImperialConverter"
        )
