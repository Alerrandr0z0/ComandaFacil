from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.dependencies import CurrentTenantId, DbSession
from app.payment.application.commands import PaymentService
from app.payment.domain.enums import PaymentMethod
from app.payment.infrastructure.pg_repository import SQLAlchemyPaymentRepository
from app.payment.infrastructure.stripe_gateway import StripeGateway
from app.settings import get_settings
from app.shared.money import Money

router = APIRouter(prefix="/payments", tags=["Payments"])


class PaymentRequestSchema(BaseModel):
    """Pydantic schema representing a request to process a new payment transaction."""

    order_id: int = Field(..., description="Unique order identifier")
    amount: Decimal = Field(..., gt=0, description="Amount to be processed")
    method: str = Field(
        ..., description="Payment method to use: CASH, CREDIT_CARD, DEBIT_CARD, or PIX"
    )

    model_config = ConfigDict(frozen=True)


class PaymentRefundSchema(BaseModel):
    """Pydantic schema representing a request to refund a completed payment."""

    order_id: int = Field(..., description="Unique order identifier")

    model_config = ConfigDict(frozen=True)


class PaymentResponseSchema(BaseModel):
    """Pydantic schema representing a completed payment response."""

    id: int
    order_id: int
    tenant_id: str
    amount: Decimal
    method: str
    status: str
    gateway_ref: str | None = None
    failure_reason: str | None = None

    model_config = ConfigDict(from_attributes=True, frozen=True)


@router.post(
    "/request",
    response_model=PaymentResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Request payment transaction processing",
)
async def request_payment(
    schema: PaymentRequestSchema,
    session: DbSession,
    tenant_id: CurrentTenantId,
) -> PaymentResponseSchema:
    """Processes a new payment transaction (via Stripe or locally for cash) and persists state."""
    # Resolve PaymentMethod enum
    try:
        method_enum = PaymentMethod(schema.method)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid payment method '{schema.method}'. Expected: CASH, CREDIT_CARD, DEBIT_CARD, PIX.",
        ) from e

    repo = SQLAlchemyPaymentRepository(session)
    settings = get_settings()

    # Poly-strategy selection
    gateway = StripeGateway(settings.stripe_secret_key)

    try:
        service = PaymentService(repo, gateway)
        payment = await service.request_payment(
            order_id=schema.order_id,
            amount=Money(schema.amount),
            method=method_enum,
            tenant_id=tenant_id,
        )
        await session.commit()

        return PaymentResponseSchema(
            id=payment.id,
            order_id=payment.order_id,
            tenant_id=payment.tenant_id,
            amount=payment.amount.amount,
            method=payment.method.value,
            status=payment.status.value,
            gateway_ref=payment.gateway_ref,
            failure_reason=payment.failure_reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    finally:
        await gateway.close()


@router.post(
    "/refund",
    response_model=PaymentResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Refund a completed payment transaction",
)
async def refund_payment(
    schema: PaymentRefundSchema,
    session: DbSession,
    tenant_id: CurrentTenantId,
) -> PaymentResponseSchema:
    """Processes a refund transaction through external Stripe gateway or locally for cash."""
    repo = SQLAlchemyPaymentRepository(session)
    settings = get_settings()

    gateway = StripeGateway(settings.stripe_secret_key)

    try:
        service = PaymentService(repo, gateway)
        payment = await service.refund_payment(order_id=schema.order_id, tenant_id=tenant_id)
        await session.commit()

        return PaymentResponseSchema(
            id=payment.id,
            order_id=payment.order_id,
            tenant_id=payment.tenant_id,
            amount=payment.amount.amount,
            method=payment.method.value,
            status=payment.status.value,
            gateway_ref=payment.gateway_ref,
            failure_reason=payment.failure_reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    finally:
        await gateway.close()


@router.get(
    "/order/{order_id}",
    response_model=PaymentResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Get payment record by Order ID",
)
async def get_payment_by_order(
    order_id: int,
    session: DbSession,
    tenant_id: CurrentTenantId,
) -> PaymentResponseSchema:
    """Fetches the payment transaction records for a specific order under the tenant."""
    repo = SQLAlchemyPaymentRepository(session)
    payment = await repo.find_by_order(order_id, tenant_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment record for order {order_id} not found.",
        )

    return PaymentResponseSchema(
        id=payment.id,
        order_id=payment.order_id,
        tenant_id=payment.tenant_id,
        amount=payment.amount.amount,
        method=payment.method.value,
        status=payment.status.value,
        gateway_ref=payment.gateway_ref,
        failure_reason=payment.failure_reason,
    )
