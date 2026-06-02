from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import httpx

from app.payment.domain.enums import PaymentMethod
from app.payment.domain.gateway import GatewayResponse

if TYPE_CHECKING:
    from app.shared.money import Money


class StripeGateway:
    """Concrete implementation of IPaymentGateway using Stripe's public REST API via HTTPX."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client = httpx.AsyncClient(
            base_url="https://api.stripe.com",
            headers={"Authorization": f"Bearer {self._api_key}"},
            timeout=10.0,
        )

    async def charge(self, amount: Money, method: PaymentMethod) -> GatewayResponse:
        """Charges a card through Stripe's /v1/payment_intents.

        Converts the Money object into integer cents as required by Stripe's small unit standards.
        """
        # Cash payments do not run through the external Stripe processor and are auto-approved locally
        if method == PaymentMethod.CASH:
            cents_ref = int(amount.amount * 100)
            return GatewayResponse(
                success=True, gateway_ref=f"ch_cash_{cents_ref}", error_message=None
            )

        # Convert amount to cents
        cents = int(amount.amount * 100)

        try:
            # We create and confirm a PaymentIntent using the test token pm_card_visa
            data = {
                "amount": str(cents),
                "currency": "brl",
                "payment_method": "pm_card_visa",
                "confirm": "true",
                "automatic_payment_methods[enabled]": "true",
                "automatic_payment_methods[allow_redirects]": "never",
            }
            response = await self._client.post("/v1/payment_intents", data=data)

            if response.status_code == HTTPStatus.OK:
                res_json = response.json()
                if res_json.get("status") == "succeeded":
                    return GatewayResponse(
                        success=True,
                        gateway_ref=res_json.get("id"),
                        error_message=None,
                    )
                return GatewayResponse(
                    success=False,
                    gateway_ref=res_json.get("id"),
                    error_message=f"Stripe payment status: {res_json.get('status')}",
                )
            res_json = response.json()
            err = res_json.get("error", {})
            return GatewayResponse(
                success=False,
                gateway_ref=None,
                error_message=err.get("message", "Stripe API charge failed"),
            )
        except Exception as e:
            return GatewayResponse(success=False, gateway_ref=None, error_message=str(e))

    async def refund(self, gateway_ref: str, amount: Money) -> GatewayResponse:
        """Refunds a transaction through Stripe's /v1/refunds."""
        # Cash refunds are processed instantly and locally
        if gateway_ref.startswith("ch_cash_"):
            return GatewayResponse(
                success=True, gateway_ref=f"re_cash_{gateway_ref}", error_message=None
            )

        cents = int(amount.amount * 100)

        try:
            data = {
                "payment_intent": gateway_ref,
                "amount": str(cents),
            }
            response = await self._client.post("/v1/refunds", data=data)

            if response.status_code == HTTPStatus.OK:
                res_json = response.json()
                return GatewayResponse(
                    success=True,
                    gateway_ref=res_json.get("id"),
                    error_message=None,
                )
            res_json = response.json()
            err = res_json.get("error", {})
            return GatewayResponse(
                success=False,
                gateway_ref=None,
                error_message=err.get("message", "Stripe API refund failed"),
            )
        except Exception as e:
            return GatewayResponse(success=False, gateway_ref=None, error_message=str(e))

    async def close(self) -> None:
        """Closes the underlying HTTPX client session."""
        await self._client.aclose()
