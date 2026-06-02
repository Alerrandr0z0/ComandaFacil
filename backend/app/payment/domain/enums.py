from __future__ import annotations

from enum import Enum


class PaymentMethod(Enum):
    """Enumeration of accepted payment methods."""

    CASH = "CASH"
    CREDIT_CARD = "CREDIT_CARD"
    DEBIT_CARD = "DEBIT_CARD"
    PIX = "PIX"


class PaymentStatus(Enum):
    """Enumeration of payment transaction processing states."""

    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"
