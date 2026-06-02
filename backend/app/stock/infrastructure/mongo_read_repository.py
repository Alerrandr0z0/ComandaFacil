from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase


class MongoStockReadRepository:
    """Reads stock items from MongoDB 'stock_read' collection."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:  # type: ignore[type-arg]
        self._collection = db["stock_read"]

    async def find_by_id(self, stock_item_id: int, tenant_id: str) -> dict[str, Any] | None:
        doc = await self._collection.find_one(
            {"stock_item_id": stock_item_id, "tenant_id": tenant_id},
            {"_id": 0},
        )
        return doc if doc else None

    async def find_all(self, tenant_id: str) -> list[dict[str, Any]]:
        cursor = self._collection.find(
            {"tenant_id": tenant_id},
            {"_id": 0},
        )
        return await cursor.to_list(length=None)

    async def find_low_stock(self, tenant_id: str) -> list[dict[str, Any]]:
        cursor = self._collection.find(
            {"tenant_id": tenant_id, "is_low_stock": True},
            {"_id": 0},
        )
        return await cursor.to_list(length=None)
