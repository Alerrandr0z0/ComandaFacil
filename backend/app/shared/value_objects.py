from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING, Final

from app.stock.domain.converters import ImperialConverter, MetricConverter

if TYPE_CHECKING:
    from app.stock.domain.converters import UnitConverter

CEP_LENGTH: Final[int] = 8


@dataclass(frozen=True)
class Email:
    """Value object for validated email addresses."""

    value: str

    def __post_init__(self) -> None:
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
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


@dataclass(frozen=True)
class Address:
    """Value object for validated shipping/delivery address."""

    street: str
    number: str
    neighborhood: str
    city: str
    state: str
    postal_code: str

    def __post_init__(self) -> None:
        # Validação simples de campos não vazios
        for field_name, value in [
            ("street", self.street),
            ("number", self.number),
            ("neighborhood", self.neighborhood),
            ("city", self.city),
            ("state", self.state),
            ("postal_code", self.postal_code),
        ]:
            if not value or not value.strip():
                raise ValueError(f"Campo do endereço '{field_name}' não pode ser vazio.")

        # Validação de formato de CEP básico
        clean_cep = re.sub(r"\D", "", self.postal_code)
        if len(clean_cep) != CEP_LENGTH:
            raise ValueError(
                f"CEP inválido: '{self.postal_code}'. Deve conter {CEP_LENGTH} dígitos."
            )

    def __str__(self) -> str:
        return f"{self.street}, {self.number} - {self.neighborhood}, {self.city}/{self.state} ({self.postal_code})"
