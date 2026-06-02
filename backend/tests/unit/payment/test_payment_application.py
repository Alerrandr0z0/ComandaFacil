from __future__ import annotations

import pytest

from app.payment.application.commands import (
    PaymentService,
    RefundPaymentCommand,
    RefundPaymentHandler,
    RequestPaymentCommand,
    RequestPaymentHandler,
)
from app.payment.domain.enums import PaymentMethod, PaymentStatus
from app.payment.domain.gateway import GatewayResponse
from app.payment.domain.payment import Payment
from app.shared.money import Money


class InMemoryPaymentRepository:
    def __init__(self) -> None:
        self._payments: dict[int, Payment] = {}
        self._next_id: int = 1

    async def find_by_id(self, id: int, tenant_id: str) -> Payment | None:
        p = self._payments.get(id)
        return p if p and p.tenant_id == tenant_id else None

    async def find_by_order(self, order_id: int, tenant_id: str) -> Payment | None:
        for p in self._payments.values():
            if p.order_id == order_id and p.tenant_id == tenant_id:
                return p
        return None

    async def save(self, payment: Payment) -> None:
        if payment.id == 0:
            payment.id = self._next_id
            self._next_id += 1
        self._payments[payment.id] = payment


class MockGateway:
    def __init__(self, charge_result: GatewayResponse | None = None) -> None:
        self.charge_result = charge_result or GatewayResponse(
            success=True, gateway_ref="pi_mock_001", error_message=None
        )
        self.refund_result: GatewayResponse = GatewayResponse(
            success=True, gateway_ref="re_mock_001", error_message=None
        )
        self.charge_calls: list[tuple[Money, PaymentMethod]] = []
        self.refund_calls: list[tuple[str, Money]] = []

    async def charge(self, amount: Money, method: PaymentMethod) -> GatewayResponse:
        self.charge_calls.append((amount, method))
        return self.charge_result

    async def refund(self, gateway_ref: str, amount: Money) -> GatewayResponse:
        self.refund_calls.append((gateway_ref, amount))
        return self.refund_result


@pytest.fixture
def repo() -> InMemoryPaymentRepository:
    return InMemoryPaymentRepository()


@pytest.fixture
def success_gateway() -> MockGateway:
    return MockGateway()


@pytest.fixture
def fail_gateway() -> MockGateway:
    return MockGateway(
        charge_result=GatewayResponse(
            success=False, gateway_ref=None, error_message="Card declined."
        )
    )


@pytest.mark.unit
async def test_request_payment_handler_success(
    repo: InMemoryPaymentRepository, success_gateway: MockGateway
) -> None:
    # Arrange
    handler = RequestPaymentHandler(repo, success_gateway)
    command = RequestPaymentCommand(
        order_id=1,
        amount=Money.from_float(100.0),
        method=PaymentMethod.CREDIT_CARD,
        tenant_id="franquia_001",
    )

    # Act
    payment = await handler.handle(command)

    # Assert
    assert payment.order_id == 1
    assert payment.status == PaymentStatus.CONFIRMED
    assert payment.gateway_ref == "pi_mock_001"
    assert payment.failure_reason is None
    assert len(success_gateway.charge_calls) == 1


@pytest.mark.unit
async def test_request_payment_handler_gateway_failure(
    repo: InMemoryPaymentRepository, fail_gateway: MockGateway
) -> None:
    # Arrange
    handler = RequestPaymentHandler(repo, fail_gateway)
    command = RequestPaymentCommand(
        order_id=2,
        amount=Money.from_float(200.0),
        method=PaymentMethod.CREDIT_CARD,
        tenant_id="franquia_001",
    )

    # Act
    payment = await handler.handle(command)

    # Assert
    assert payment.order_id == 2
    assert payment.status == PaymentStatus.FAILED
    assert payment.gateway_ref is None
    assert payment.failure_reason == "Card declined."
    assert len(fail_gateway.charge_calls) == 1


@pytest.mark.unit
async def test_request_payment_handler_cash_auto_confirms(
    repo: InMemoryPaymentRepository, success_gateway: MockGateway
) -> None:
    # Arrange
    handler = RequestPaymentHandler(repo, success_gateway)
    command = RequestPaymentCommand(
        order_id=3,
        amount=Money.from_float(50.0),
        method=PaymentMethod.CASH,
        tenant_id="franquia_001",
    )

    # Act
    payment = await handler.handle(command)

    # Assert
    assert payment.order_id == 3
    assert payment.status == PaymentStatus.CONFIRMED
    assert len(success_gateway.charge_calls) == 1


@pytest.mark.unit
async def test_request_payment_handler_duplicate_confirmed_returns_existing(
    repo: InMemoryPaymentRepository, success_gateway: MockGateway
) -> None:
    # Arrange
    handler = RequestPaymentHandler(repo, success_gateway)
    existing = Payment(id=10, order_id=5, tenant_id="franquia_001",
                       amount=Money.from_float(50.0), method=PaymentMethod.CASH)
    existing.confirm("ch_cash_5000")
    await repo.save(existing)
    command = RequestPaymentCommand(
        order_id=5,
        amount=Money.from_float(75.0),
        method=PaymentMethod.CREDIT_CARD,
        tenant_id="franquia_001",
    )

    # Act
    payment = await handler.handle(command)

    # Assert
    assert payment.id == 10
    assert payment.status == PaymentStatus.CONFIRMED
    assert payment.gateway_ref == "ch_cash_5000"
    assert len(success_gateway.charge_calls) == 0


@pytest.mark.unit
async def test_refund_payment_handler_success(
    repo: InMemoryPaymentRepository, success_gateway: MockGateway
) -> None:
    # Arrange
    handler = RefundPaymentHandler(repo, success_gateway)
    payment = Payment(id=20, order_id=10, tenant_id="franquia_001",
                      amount=Money.from_float(100.0), method=PaymentMethod.CREDIT_CARD)
    payment.confirm("pi_orig_001")
    await repo.save(payment)
    command = RefundPaymentCommand(order_id=10, tenant_id="franquia_001")

    # Act
    result = await handler.handle(command)

    # Assert
    assert result.status == PaymentStatus.REFUNDED
    assert len(success_gateway.refund_calls) == 1


@pytest.mark.unit
async def test_refund_payment_handler_not_found_raises_error(
    repo: InMemoryPaymentRepository, success_gateway: MockGateway
) -> None:
    # Arrange
    handler = RefundPaymentHandler(repo, success_gateway)
    command = RefundPaymentCommand(order_id=999, tenant_id="franquia_001")

    # Act & Assert
    with pytest.raises(ValueError, match="No payment record found for order 999"):
        await handler.handle(command)


@pytest.mark.unit
async def test_refund_payment_handler_wrong_state_raises_error(
    repo: InMemoryPaymentRepository, success_gateway: MockGateway
) -> None:
    # Arrange
    handler = RefundPaymentHandler(repo, success_gateway)
    payment = Payment(id=30, order_id=11, tenant_id="franquia_001",
                      amount=Money.from_float(50.0), method=PaymentMethod.PIX)
    await repo.save(payment)
    command = RefundPaymentCommand(order_id=11, tenant_id="franquia_001")

    # Act & Assert
    with pytest.raises(ValueError, match="Cannot refund a payment in status PENDING"):
        await handler.handle(command)


@pytest.mark.unit
async def test_payment_service_facade_request(
    repo: InMemoryPaymentRepository, success_gateway: MockGateway
) -> None:
    # Arrange
    service = PaymentService(repo, success_gateway)

    # Act
    payment = await service.request_payment(
        order_id=50,
        amount=Money.from_float(200.0),
        method=PaymentMethod.PIX,
        tenant_id="franquia_001",
    )

    # Assert
    assert payment.order_id == 50
    assert payment.status == PaymentStatus.CONFIRMED
