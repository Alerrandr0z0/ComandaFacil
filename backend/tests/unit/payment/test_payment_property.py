from __future__ import annotations

from decimal import Decimal

import pytest
from hypothesis import given, strategies as st

from app.payment.domain.enums import PaymentMethod, PaymentStatus
from app.payment.domain.payment import Payment
from app.shared.money import Money


TENANT_IDS = st.sampled_from(["franquia_001", "franquia_002", "franquia_003"])
AMOUNTS = st.decimals(min_value=Decimal("0.01"), max_value=Decimal("10000.00"), places=2)
METHODS = st.sampled_from(list(PaymentMethod))
STATES = st.sampled_from(list(PaymentStatus))
TXN_REFS = st.text(min_size=5, max_size=30, alphabet="abcdefghijklmnopqrstuvwxyz_0123456789")
FAIL_REASONS = st.text(min_size=3, max_size=100)


def _make_payment(
    payment_id: int = 1,
    order_id: int = 1,
    tenant_id: str = "franquia_001",
    amount_val: Decimal = Decimal("50.00"),
    method: PaymentMethod = PaymentMethod.PIX,
) -> Payment:
    return Payment(
        id=payment_id,
        order_id=order_id,
        tenant_id=tenant_id,
        amount=Money(amount_val),
        method=method,
    )


@pytest.mark.hypothesis
@given(amount=AMOUNTS, method=METHODS)
def test_payment_initial_state_property(amount: Decimal, method: PaymentMethod) -> None:
    # Arrange & Act
    payment = _make_payment(amount_val=amount, method=method)

    # Assert — invariants for any freshly created Payment
    assert payment.status == PaymentStatus.PENDING
    assert payment.gateway_ref is None
    assert payment.failure_reason is None
    assert isinstance(payment.amount, Money)
    assert payment.amount.amount >= Decimal("0.01")


@pytest.mark.hypothesis
@given(ref=TXN_REFS)
def test_payment_confirm_postcondition_property(ref: str) -> None:
    # Arrange
    payment = _make_payment()

    # Act
    payment.confirm(gateway_ref=ref)

    # Assert
    assert payment.status == PaymentStatus.CONFIRMED
    assert payment.gateway_ref == ref
    assert payment.failure_reason is None


@pytest.mark.hypothesis
@given(reason=FAIL_REASONS)
def test_payment_fail_postcondition_property(reason: str) -> None:
    # Arrange
    payment = _make_payment()

    # Act
    payment.fail(reason=reason)

    # Assert
    assert payment.status == PaymentStatus.FAILED
    assert payment.failure_reason == reason
    assert payment.gateway_ref is None


@pytest.mark.hypothesis
@given(ref=TXN_REFS)
def test_payment_refund_roundtrip_property(ref: str) -> None:
    # Arrange
    payment = _make_payment()
    payment.confirm(gateway_ref=ref)
    original_ref = payment.gateway_ref

    # Act
    payment.refund()

    # Assert — refund preserves gateway_ref but clears nothing
    assert payment.status == PaymentStatus.REFUNDED
    assert payment.gateway_ref == original_ref == ref


@pytest.mark.hypothesis
@given(amount=AMOUNTS, method=METHODS, ref=TXN_REFS, reason=FAIL_REASONS)
def test_payment_terminal_state_invariant_property(
    amount: Decimal, method: PaymentMethod, ref: str, reason: str
) -> None:
    # Arrangements
    terminal_states: list[Payment] = []
    p1 = _make_payment(amount_val=amount, method=method)
    p1.confirm(ref)
    terminal_states.append(p1)

    p2 = _make_payment(amount_val=amount, method=method)
    p2.fail(reason)
    terminal_states.append(p2)

    p3 = _make_payment(amount_val=amount, method=method)
    p3.confirm(ref)
    p3.refund()
    terminal_states.append(p3)

    for p in terminal_states:
        # Invariant: no terminal payment can be re-confirmed
        with pytest.raises(ValueError):
            p.confirm("another_ref")

        # Invariant: no terminal payment can be failed
        with pytest.raises(ValueError):
            p.fail("another reason")

        # Invariant: only CONFIRMED can be refunded (REFUNDED cannot re-refund)
        if p.status == PaymentStatus.REFUNDED:
            with pytest.raises(ValueError):
                p.refund()


@pytest.mark.hypothesis
@given(amount=AMOUNTS, reason=FAIL_REASONS)
def test_payment_failed_mutual_exclusion_property(
    amount: Decimal, reason: str
) -> None:
    # Arrange
    payment = _make_payment(amount_val=amount)
    payment.fail(reason)

    # Assert — failed payment has reason but NO gateway_ref
    assert payment.failure_reason == reason
    assert payment.gateway_ref is None
    assert payment.status == PaymentStatus.FAILED


@pytest.mark.hypothesis
@given(amount=AMOUNTS, ref=TXN_REFS)
def test_payment_confirmed_mutual_exclusion_property(
    amount: Decimal, ref: str
) -> None:
    # Arrange
    payment = _make_payment(amount_val=amount)
    payment.confirm(ref)

    # Assert — confirmed payment has gateway_ref but NO failure_reason
    assert payment.gateway_ref == ref
    assert payment.failure_reason is None
    assert payment.status == PaymentStatus.CONFIRMED


@pytest.mark.hypothesis
@given(amount_1=AMOUNTS, amount_2=AMOUNTS, ref=TXN_REFS)
def test_payment_unique_instances_independent_property(
    amount_1: Decimal, amount_2: Decimal, ref: str
) -> None:
    # Arrange — two independent payments
    p1 = _make_payment(payment_id=1, order_id=1, amount_val=amount_1, method=PaymentMethod.CREDIT_CARD)
    p2 = _make_payment(payment_id=2, order_id=2, amount_val=amount_2, method=PaymentMethod.PIX)

    # Act — different transitions on each
    p1.confirm(ref)
    p2.fail("Timeout")

    # Assert — no cross-instance state leakage
    assert p1.status == PaymentStatus.CONFIRMED
    assert p1.failure_reason is None
    assert p2.status == PaymentStatus.FAILED
    assert p2.gateway_ref is None
