from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase


class MongoMenuReadRepository:
    """Reads Menu read models from MongoDB 'menu_read_models' collection."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:  # type: ignore[type-arg]
        self._collection = db["menu_read_models"]

    async def find_by_id(
        self, menu_id: int, tenant_id: str
    ) -> dict[str, Any] | None:
        doc = await self._collection.find_one(
            {"menu_id": menu_id, "tenant_id": tenant_id},
            {"_id": 0},
        )
        return doc if doc else None

    async def find_all(self, tenant_id: str) -> list[dict[str, Any]]:
        cursor = self._collection.find(
            {"tenant_id": tenant_id},
            {"_id": 0},
        )
        return await cursor.to_list(length=None)
