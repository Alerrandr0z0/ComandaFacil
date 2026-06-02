from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase


class MongoKitchenReadRepository:
    """Reads kitchen items from MongoDB 'kitchen_read' collection."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:  # type: ignore[type-arg]
        self._collection = db["kitchen_read"]

    async def find_active_by_station(
        self, station_type: str, tenant_id: str
    ) -> list[dict[str, Any]]:
        cursor = self._collection.find(
            {
                "tenant_id": tenant_id,
                "station_type_cpy": station_type,
                "state": {"$in": ["WAITING", "PREPARING"]},
            },
            {"_id": 0},
        )
        return await cursor.to_list(length=None)
