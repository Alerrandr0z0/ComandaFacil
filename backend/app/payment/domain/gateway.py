from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from app.payment.domain.enums import PaymentMethod
    from app.shared.money import Money


@dataclass(frozen=True)
class GatewayResponse:
    """Value Object representing the processed transaction response from a payment gateway."""

    success: bool
    gateway_ref: str | None
    error_message: str | None


@runtime_checkable
class IPaymentGateway(Protocol):
    """Strategy protocol for executing payment transactions via external gateways (Stripe, etc.)."""

    async def charge(self, amount: Money, method: PaymentMethod) -> GatewayResponse:
        """Charges a specific amount through the gateway with the chosen method."""
        ...

    async def refund(self, gateway_ref: str, amount: Money) -> GatewayResponse:
        """Refunds a previously charged transaction through the gateway."""
        ...
