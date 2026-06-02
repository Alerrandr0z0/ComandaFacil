from __future__ import annotations

from typing import TYPE_CHECKING

from app.payment.domain.enums import PaymentMethod, PaymentStatus

if TYPE_CHECKING:
    from app.shared.money import Money


class Payment:
    """Aggregate Root representing a payment transaction for an OrderForm."""

    def __init__(
        self,
        id: int,
        order_id: int,
        tenant_id: str,
        amount: Money,
        method: PaymentMethod,
    ) -> None:
        self.id: int = id
        self.order_id: int = order_id
        self.tenant_id: str = tenant_id
        self.amount: Money = amount
        self.method: PaymentMethod = method
        self._status: PaymentStatus = PaymentStatus.PENDING
        self._gateway_ref: str | None = None
        self._failure_reason: str | None = None

    @property
    def status(self) -> PaymentStatus:
        """Returns the current processing state of the payment."""
        return self._status

    @property
    def gateway_ref(self) -> str | None:
        """Returns the gateway transaction reference identifier if processed."""
        return self._gateway_ref

    @property
    def failure_reason(self) -> str | None:
        """Returns the failure reason if the payment failed."""
        return self._failure_reason

    def confirm(self, gateway_ref: str) -> None:
        """Confirms payment after successful gateway charge."""
        if self._status != PaymentStatus.PENDING:
            raise ValueError("Cannot confirm a terminal payment.")
        self._status = PaymentStatus.CONFIRMED
        self._gateway_ref = gateway_ref

    def fail(self, reason: str) -> None:
        """Marks payment as failed due to a gateway error or cash cancellation."""
        if self._status != PaymentStatus.PENDING:
            raise ValueError("Cannot fail a terminal payment.")
        self._status = PaymentStatus.FAILED
        self._failure_reason = reason

    def refund(self) -> None:
        """Refunds a completed payment."""
        if self._status != PaymentStatus.CONFIRMED:
            raise ValueError("Can only refund a CONFIRMED payment.")
        self._status = PaymentStatus.REFUNDED

    def __repr__(self) -> str:
        return (
            f"Payment(id={self.id}, order_id={self.order_id}, tenant_id={self.tenant_id!r}, "
            f"amount={self.amount}, method={self.method.name}, status={self.status.name})"
        )
