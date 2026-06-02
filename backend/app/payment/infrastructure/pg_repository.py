from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from app.payment.domain.enums import PaymentMethod, PaymentStatus
from app.payment.domain.payment import Payment
from app.payment.infrastructure.orm_models import PaymentORM
from app.shared.money import Money

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class SQLAlchemyPaymentRepository:
    """SQLAlchemy implementation of PaymentRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_id(self, id: int, tenant_id: str) -> Payment | None:
        stmt = select(PaymentORM).where(PaymentORM.id == id, PaymentORM.tenant_id == tenant_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if not orm:
            return None
        return self._map_to_domain(orm)

    async def find_by_order(self, order_id: int, tenant_id: str) -> Payment | None:
        stmt = select(PaymentORM).where(
            PaymentORM.order_id == order_id, PaymentORM.tenant_id == tenant_id
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if not orm:
            return None
        return self._map_to_domain(orm)

    async def save(self, payment: Payment) -> None:
        stmt = select(PaymentORM).where(PaymentORM.id == payment.id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm:
            orm.order_id = payment.order_id
            orm.tenant_id = payment.tenant_id
            orm.amount = payment.amount.amount
            orm.method = payment.method.value
            orm.status = payment.status.value
            orm.gateway_ref = payment.gateway_ref
            orm.failure_reason = payment.failure_reason
        else:
            orm = PaymentORM(
                id=payment.id,
                order_id=payment.order_id,
                tenant_id=payment.tenant_id,
                amount=payment.amount.amount,
                method=payment.method.value,
                status=payment.status.value,
                gateway_ref=payment.gateway_ref,
                failure_reason=payment.failure_reason,
            )
            self._session.add(orm)

        await self._session.flush()

    def _map_to_domain(self, orm: PaymentORM) -> Payment:
        payment = Payment(
            id=orm.id,
            order_id=orm.order_id,
            tenant_id=orm.tenant_id,
            amount=Money(orm.amount),
            method=PaymentMethod(orm.method),
        )
        payment._status = PaymentStatus(orm.status)  # type: ignore[reportPrivateUsage]
        payment._gateway_ref = orm.gateway_ref  # type: ignore[reportPrivateUsage]
        return payment
