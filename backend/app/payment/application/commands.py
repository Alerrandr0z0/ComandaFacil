from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from app.payment.domain.enums import PaymentMethod, PaymentStatus
from app.payment.domain.payment import Payment

if TYPE_CHECKING:
    from app.payment.domain.gateway import IPaymentGateway
    from app.payment.domain.repository import PaymentRepository
    from app.shared.money import Money


@dataclass(frozen=True)
class RequestPaymentCommand:
    order_id: int
    amount: Money
    method: PaymentMethod
    tenant_id: str

    def __repr__(self) -> str:
        return (
            f"RequestPaymentCommand(order_id={self.order_id}, amount={self.amount}, "
            f"method={self.method.name}, tenant={self.tenant_id!r})"
        )


class RequestPaymentHandler:
    def __init__(self, repo: PaymentRepository, gateway: IPaymentGateway) -> None:
        self._repo: Final[PaymentRepository] = repo
        self._gateway: Final[IPaymentGateway] = gateway

    async def handle(self, command: RequestPaymentCommand) -> Payment:
        # Check if a confirmed/refunded transaction already exists for this order
        existing = await self._repo.find_by_order(command.order_id, command.tenant_id)
        if existing and existing.status in (PaymentStatus.CONFIRMED, PaymentStatus.REFUNDED):
            return existing

        # Create new transient Payment record (ID=0, database will assign sequential PK upon flush)
        payment = Payment(
            id=0,
            order_id=command.order_id,
            tenant_id=command.tenant_id,
            amount=command.amount,
            method=command.method,
        )
        await self._repo.save(payment)

        # Process charge through our polymorphic payment gateway strategy
        response = await self._gateway.charge(command.amount, command.method)

        if response.success:
            payment.confirm(gateway_ref=response.gateway_ref or "local_txn")
        else:
            payment.fail(reason=response.error_message or "Gateway charge failed")

        # Save final transaction status
        await self._repo.save(payment)
        return payment


@dataclass(frozen=True)
class RefundPaymentCommand:
    order_id: int
    tenant_id: str

    def __repr__(self) -> str:
        return f"RefundPaymentCommand(order_id={self.order_id}, tenant={self.tenant_id!r})"


class RefundPaymentHandler:
    def __init__(self, repo: PaymentRepository, gateway: IPaymentGateway) -> None:
        self._repo: Final[PaymentRepository] = repo
        self._gateway: Final[IPaymentGateway] = gateway

    async def handle(self, command: RefundPaymentCommand) -> Payment:
        payment = await self._repo.find_by_order(command.order_id, command.tenant_id)
        if not payment:
            raise ValueError(f"No payment record found for order {command.order_id}.")

        if payment.status != PaymentStatus.CONFIRMED:
            raise ValueError(f"Cannot refund a payment in status {payment.status.name}.")

        # If payment intent exists and is an external credit/debit card, process through gateway
        if payment.gateway_ref and not payment.gateway_ref.startswith("ch_cash_"):
            response = await self._gateway.refund(payment.gateway_ref, payment.amount)
            if not response.success:
                raise ValueError(f"Stripe refund failed: {response.error_message}")

        # Transition Domain Aggregate state
        payment.refund()
        await self._repo.save(payment)
        return payment


class PaymentService:
    """Facade Service matching UML PaymentService definition."""

    def __init__(self, repo: PaymentRepository, gateway: IPaymentGateway) -> None:
        self._repo = repo
        self._gateway = gateway
        self._request_handler = RequestPaymentHandler(repo, gateway)
        self._refund_handler = RefundPaymentHandler(repo, gateway)

    async def request_payment(
        self, order_id: int, amount: Money, method: PaymentMethod, tenant_id: str
    ) -> Payment:
        cmd = RequestPaymentCommand(
            order_id=order_id, amount=amount, method=method, tenant_id=tenant_id
        )
        return await self._request_handler.handle(cmd)

    async def refund_payment(self, order_id: int, tenant_id: str) -> Payment:
        cmd = RefundPaymentCommand(order_id=order_id, tenant_id=tenant_id)
        return await self._refund_handler.handle(cmd)
