from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.kitchen.domain.kitchen_item import KitchenOrderItem


class KitchenReadModelSync:
    """Syncs KitchenOrderItem aggregate to MongoDB 'kitchen_read' collection for analytics."""

    def __init__(self, mongo_db: Any) -> None:
        self._collection = mongo_db["kitchen_read"]

    async def sync(self, item: KitchenOrderItem) -> None:
        now = datetime.datetime.now(datetime.UTC)
        started_at: datetime.datetime | None = None
        completed_at: datetime.datetime | None = None

        state = item.state.name
        if state in ("PREPARING", "READY", "CANCELLED"):
            started_at = now
        if state in ("READY", "CANCELLED"):
            completed_at = now

        doc = {
            "kitchen_item_id": item.id,
            "correlation_id": item.correlation_id,
            "tenant_id": item.tenant_id,
            "name_cpy": item.name_cpy,
            "station_type_cpy": item.station_type_cpy,
            "state": state,
            "started_at": started_at,
            "completed_at": completed_at,
            "created_at": now,
        }

        await self._collection.replace_one(
            {"kitchen_item_id": item.id, "tenant_id": item.tenant_id},
            doc,
            upsert=True,
        )
