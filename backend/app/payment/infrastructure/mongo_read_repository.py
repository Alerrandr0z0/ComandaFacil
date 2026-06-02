from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase


class MongoPaymentReadRepository:
    """Reads payment records from MongoDB 'payments_read' collection."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:  # type: ignore[type-arg]
        self._collection = db["payments_read"]

    async def find_by_order(self, order_id: int, tenant_id: str) -> dict[str, Any] | None:
        doc = await self._collection.find_one(
            {"order_id": order_id, "tenant_id": tenant_id},
            {"_id": 0},
        )
        return doc if doc else None

    async def find_by_id(self, payment_id: int, tenant_id: str) -> dict[str, Any] | None:
        doc = await self._collection.find_one(
            {"payment_id": payment_id, "tenant_id": tenant_id},
            {"_id": 0},
        )
        return doc if doc else None
