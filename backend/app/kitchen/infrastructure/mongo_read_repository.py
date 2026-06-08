from __future__ import annotations

import datetime
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
        fifteen_minutes_ago = datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=15)
        cursor = self._collection.find(
            {
                "tenant_id": tenant_id,
                "station_type_cpy": station_type,
            },
            {"_id": 0},
        )
        all_items = await cursor.to_list(length=None)

        active_items = []
        for item in all_items:
            state = item.get("state")
            if state in ("WAITING", "PREPARING"):
                active_items.append(item)
            elif state in ("READY", "CANCELLED"):
                completed_at_val = item.get("completed_at")
                if completed_at_val:
                    if isinstance(completed_at_val, str):
                        try:
                            completed_at = datetime.datetime.fromisoformat(completed_at_val)
                        except ValueError:
                            completed_at = datetime.datetime.now(datetime.UTC)
                    else:
                        completed_at = completed_at_val

                    if completed_at.tzinfo is None:
                        completed_at = completed_at.replace(tzinfo=datetime.UTC)
                    if completed_at >= fifteen_minutes_ago:
                        active_items.append(item)

        return active_items
