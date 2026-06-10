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
        state = item.state.name

        is_preparing = state in ("PREPARING", "READY", "CANCELLED")
        is_final = state in ("READY", "CANCELLED")

        set_fields: dict[str, object] = {
            "correlation_id": item.correlation_id,
            "name_cpy": item.name_cpy,
            "station_type_cpy": item.station_type_cpy,
            "preparation_profile": item.preparation_profile,
            "notes": item.notes,
            "state": state,
            "tenant_id": item.tenant_id,
        }

        if is_final:
            set_fields["completed_at"] = now

        set_on_insert: dict[str, object] = {}
        if is_preparing:
            set_on_insert["started_at"] = now

        await self._collection.update_one(
            {"kitchen_item_id": item.id, "tenant_id": item.tenant_id},
            {"$set": set_fields, "$setOnInsert": set_on_insert},
            upsert=True,
        )
