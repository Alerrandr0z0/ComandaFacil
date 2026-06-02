from __future__ import annotations

import pytest

from app.payment.domain.enums import PaymentMethod, PaymentStatus
from app.payment.domain.gateway import GatewayResponse
from app.payment.domain.payment import Payment
from app.shared.money import Money


def test_create_payment_when_valid_params_then_initializes_with_pending_state() -> None:
    # Arrange
    payment_id = 1
    order_id = 42
    tenant_id = "franquia_001"
    amount = Money.from_float(99.90)
    method = PaymentMethod.CREDIT_CARD

    # Act
    payment = Payment(
        id=payment_id,
        order_id=order_id,
        tenant_id=tenant_id,
        amount=amount,
        method=method,
    )

    # Assert
    assert payment.id == payment_id
    assert payment.order_id == order_id
    assert payment.tenant_id == tenant_id
    assert payment.amount == amount
    assert payment.method == method
    assert payment.status == PaymentStatus.PENDING
    assert payment.gateway_ref is None


def test_payment_confirm_when_pending_then_transitions_to_confirmed() -> None:
    # Arrange
    payment = Payment(1, 42, "franquia_001", Money.from_float(50.0), PaymentMethod.PIX)

    # Act
    payment.confirm(gateway_ref="tr_pix_123")

    # Assert
    assert payment.status == PaymentStatus.CONFIRMED
    assert payment.gateway_ref == "tr_pix_123"


def test_payment_fail_when_pending_then_transitions_to_failed() -> None:
    # Arrange
    payment = Payment(1, 42, "franquia_001", Money.from_float(50.0), PaymentMethod.PIX)

    # Act
    payment.fail(reason="Insufficient funds")

    # Assert
    assert payment.status == PaymentStatus.FAILED
    assert payment.failure_reason == "Insufficient funds"


def test_payment_refund_when_confirmed_then_transitions_to_refunded() -> None:
    # Arrange
    payment = Payment(1, 42, "franquia_001", Money.from_float(50.0), PaymentMethod.PIX)
    payment.confirm("tr_pix_123")

    # Act
    payment.refund()

    # Assert
    assert payment.status == PaymentStatus.REFUNDED


def test_payment_invalid_transitions_then_raises_value_error() -> None:
    # Arrange
    payment = Payment(1, 42, "franquia_001", Money.from_float(50.0), PaymentMethod.PIX)

    # Act & Assert 1: Cannot refund a pending payment
    with pytest.raises(ValueError, match="Can only refund a CONFIRMED payment"):
        payment.refund()

    # Act & Assert 2: Cannot confirm a failed payment
    payment.fail("Expired")
    with pytest.raises(ValueError, match="Cannot confirm a terminal payment"):
        payment.confirm("tr_123")

    # Arrange 2: Confirmed payment
    payment2 = Payment(2, 42, "franquia_001", Money.from_float(25.0), PaymentMethod.CASH)
    payment2.confirm("tr_cash")

    # Act & Assert 3: Cannot fail a confirmed payment
    with pytest.raises(ValueError, match="Cannot fail a terminal payment"):
        payment2.fail("Cancelled")


def test_gateway_response_value_object() -> None:
    # Act
    res = GatewayResponse(success=True, gateway_ref="ch_stripe_999", error_message=None)

    # Assert
    assert res.success is True
    assert res.gateway_ref == "ch_stripe_999"
    assert res.error_message is None
