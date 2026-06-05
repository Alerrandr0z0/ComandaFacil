from __future__ import annotations

from enum import StrEnum


class TransactionType(StrEnum):
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"
    ADJUSTMENT = "ADJUSTMENT"
    PRODUCTION = "PRODUCTION"
    WASTE = "WASTE"


class StockCategory(StrEnum):
    RAW_MATERIAL = "RAW_MATERIAL"
    SUPPLEMENT = "SUPPLEMENT"
    PACKAGING = "PACKAGING"
    BEVERAGE = "BEVERAGE"
    OTHER = "OTHER"
