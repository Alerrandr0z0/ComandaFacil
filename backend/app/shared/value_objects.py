import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

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

    amount: float
    unit: MeasurementUnit

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError(f"Quantidade não pode ser negativa: {self.amount}")

    def __str__(self) -> str:
        return f"{self.amount}{self.unit.value}"


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
