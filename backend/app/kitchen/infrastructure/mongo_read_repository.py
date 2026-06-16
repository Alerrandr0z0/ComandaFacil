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

        active_items = [
            item for item in all_items if self._is_item_active(item, fifteen_minutes_ago)
        ]

        for item in active_items:
            _format_datetimes(item)

        return active_items

    def _is_item_active(self, item: dict[str, Any], cutoff: datetime.datetime) -> bool:
        state = item.get("state")
        if state in ("WAITING", "PREPARING", "CANCEL_REQUESTED"):
            return True
        if state in ("READY", "SURPLUS"):
            completed_at = self._parse_completed_at(item.get("completed_at"))
            return completed_at is not None and completed_at >= cutoff
        return False

    def _parse_completed_at(self, val: Any) -> datetime.datetime | None:
        if not val:
            return None
        if isinstance(val, str):
            try:
                dt = datetime.datetime.fromisoformat(val)
            except ValueError:
                return None
        else:
            dt = val

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.UTC)
        return dt


def _format_datetimes(item: dict[str, Any]) -> None:
    for field in ("created_at", "started_at", "completed_at"):
        val = item.get(field)
        if val and isinstance(val, datetime.datetime):
            if val.tzinfo is None:
                val = val.replace(tzinfo=datetime.UTC)
            item[field] = val.isoformat()
