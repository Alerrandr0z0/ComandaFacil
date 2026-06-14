from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.payment.domain.enums import PaymentMethod
from app.payment.infrastructure.stripe_gateway import StripeGateway
from app.shared.money import Money


@pytest.mark.asyncio
async def test_stripe_gateway_cash_operations() -> None:
    gateway = StripeGateway("test_key")
    try:
        # Test charge cash
        res = await gateway.charge(Money(Decimal("10.0")), PaymentMethod.CASH)
        assert res.success is True
        assert res.gateway_ref is not None
        assert "ch_cash_1000" in res.gateway_ref

        # Test refund cash
        res_ref = await gateway.refund("ch_cash_1000", Money(Decimal("10.0")))
        assert res_ref.success is True
        assert res_ref.gateway_ref is not None
        assert "re_cash_ch_cash_1000" in res_ref.gateway_ref
    finally:
        await gateway.close()


@pytest.mark.asyncio
async def test_stripe_gateway_card_charge_success() -> None:
    gateway = StripeGateway("test_key")
    try:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = lambda: {"status": "succeeded", "id": "pi_123"}

        with patch.object(gateway._client, "post", return_value=mock_response):  # pyright: ignore[reportPrivateUsage]
            res = await gateway.charge(Money(Decimal("50.0")), PaymentMethod.CREDIT_CARD)
            assert res.success is True
            assert res.gateway_ref == "pi_123"
    finally:
        await gateway.close()


@pytest.mark.asyncio
async def test_stripe_gateway_card_charge_failed_status() -> None:
    gateway = StripeGateway("test_key")
    try:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = lambda: {"status": "failed", "id": "pi_123"}

        with patch.object(gateway._client, "post", return_value=mock_response):  # pyright: ignore[reportPrivateUsage]
            res = await gateway.charge(Money(Decimal("50.0")), PaymentMethod.CREDIT_CARD)
            assert res.success is False
            assert res.error_message is not None
            assert "Stripe payment status" in res.error_message
    finally:
        await gateway.close()


@pytest.mark.asyncio
async def test_stripe_gateway_card_charge_api_error() -> None:
    gateway = StripeGateway("test_key")
    try:
        mock_response = AsyncMock()
        mock_response.status_code = 400
        mock_response.json = lambda: {"error": {"message": "Invalid card number"}}

        with patch.object(gateway._client, "post", return_value=mock_response):  # pyright: ignore[reportPrivateUsage]
            res = await gateway.charge(Money(Decimal("50.0")), PaymentMethod.CREDIT_CARD)
            assert res.success is False
            assert res.error_message == "Invalid card number"
    finally:
        await gateway.close()


@pytest.mark.asyncio
async def test_stripe_gateway_card_charge_exception() -> None:
    gateway = StripeGateway("test_key")
    try:
        with patch.object(gateway._client, "post", side_effect=Exception("Connection error")):  # pyright: ignore[reportPrivateUsage]
            res = await gateway.charge(Money(Decimal("50.0")), PaymentMethod.CREDIT_CARD)
            assert res.success is False
            assert res.error_message is not None
            assert "Connection error" in res.error_message
    finally:
        await gateway.close()


@pytest.mark.asyncio
async def test_stripe_gateway_card_refund_success() -> None:
    gateway = StripeGateway("test_key")
    try:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = lambda: {"id": "re_123"}

        with patch.object(gateway._client, "post", return_value=mock_response):  # pyright: ignore[reportPrivateUsage]
            res = await gateway.refund("pi_123", Money(Decimal("50.0")))
            assert res.success is True
            assert res.gateway_ref == "re_123"
    finally:
        await gateway.close()


@pytest.mark.asyncio
async def test_stripe_gateway_card_refund_api_error() -> None:
    gateway = StripeGateway("test_key")
    try:
        mock_response = AsyncMock()
        mock_response.status_code = 400
        mock_response.json = lambda: {"error": {"message": "Charge already refunded"}}

        with patch.object(gateway._client, "post", return_value=mock_response):  # pyright: ignore[reportPrivateUsage]
            res = await gateway.refund("pi_123", Money(Decimal("50.0")))
            assert res.success is False
            assert res.error_message == "Charge already refunded"
    finally:
        await gateway.close()


@pytest.mark.asyncio
async def test_stripe_gateway_card_refund_exception() -> None:
    gateway = StripeGateway("test_key")
    try:
        with patch.object(gateway._client, "post", side_effect=Exception("Connection error")):  # pyright: ignore[reportPrivateUsage]
            res = await gateway.refund("pi_123", Money(Decimal("50.0")))
            assert res.success is False
            assert res.error_message is not None
            assert "Connection error" in res.error_message
    finally:
        await gateway.close()
