from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.payment.domain.payment import Payment


class PaymentReadModelSync:
    """Syncs Payment aggregate to MongoDB 'payments_read' collection."""

    def __init__(self, mongo_db: Any) -> None:
        self._collection = mongo_db["payments_read"]

    async def sync(self, payment: Payment) -> None:
        doc = {
            "payment_id": payment.id,
            "order_id": payment.order_id,
            "tenant_id": payment.tenant_id,
            "amount": str(payment.amount.amount),
            "method": payment.method.value,
            "status": payment.status.value,
            "gateway_ref": payment.gateway_ref,
            "failure_reason": payment.failure_reason,
            "created_at": datetime.datetime.now(datetime.UTC).isoformat(),
        }
        await self._collection.replace_one(
            {"payment_id": payment.id},
            doc,
            upsert=True,
        )
