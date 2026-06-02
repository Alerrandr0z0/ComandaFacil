from __future__ import annotations

from enum import StrEnum


class MovementType(StrEnum):
    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"
    ADJUSTMENT = "ADJUSTMENT"


class StockCategory(StrEnum):
    RAW_MATERIAL = "RAW_MATERIAL"
    SUPPLEMENT = "SUPPLEMENT"
    PACKAGING = "PACKAGING"
    BEVERAGE = "BEVERAGE"
    OTHER = "OTHER"
