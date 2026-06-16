from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.kitchen.domain.kitchen_item import KitchenOrderItem


class KitchenReadModelSync:
    """Syncs KitchenOrderItem aggregate to MongoDB 'kitchen_read' collection for analytics."""

    def __init__(self, mongo_db: Any) -> None:
        self._collection = mongo_db["kitchen_read"]

    async def sync(self, item: KitchenOrderItem, menu_item_id: int | None = None) -> None:
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
            "previous_state": item.previous_state,
        }
        
        # Handle menu_item_id: if provided, set it. If not, try to keep existing.
        if menu_item_id is not None:
            set_fields["menu_item_id"] = menu_item_id
        else:
            existing = await self._collection.find_one(
                {"kitchen_item_id": item.id, "tenant_id": item.tenant_id},
                {"_id": 0, "menu_item_id": 1},
            )
            if existing and existing.get("menu_item_id"):
                set_fields["menu_item_id"] = existing["menu_item_id"]

        if is_final:
            set_fields["completed_at"] = now

        set_on_insert: dict[str, Any] = {
            "kitchen_item_id": item.id,
            "created_at": now,
        }

        update_doc: dict[str, Any] = {
            "$set": set_fields,
            "$setOnInsert": set_on_insert,
        }
        if is_preparing:
            update_doc["$min"] = {"started_at": now}

        await self._collection.update_one(
            {"kitchen_item_id": item.id, "tenant_id": item.tenant_id},
            update_doc,
            upsert=True,
        )
