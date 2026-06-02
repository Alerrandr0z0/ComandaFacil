from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.stock.domain.stock_item import StockItem


class StockReadModelSync:
    """Syncs StockItem aggregate to MongoDB 'stock_read' collection for analytics."""

    def __init__(self, mongo_db: Any) -> None:
        self._collection = mongo_db["stock_read"]

    async def sync(self, item: StockItem) -> None:
        doc = {
            "stock_item_id": item.id,
            "tenant_id": item.tenant_id,
            "name": item.name,
            "category": item.category,
            "current_quantity": item.current_quantity.amount,
            "unit": item.current_quantity.unit.value,
            "min_stock_level": item.min_stock_level,
            "is_low_stock": item.is_low_stock,
            "is_active": item.is_active,
        }

        await self._collection.replace_one(
            {"stock_item_id": item.id, "tenant_id": item.tenant_id},
            doc,
            upsert=True,
        )

    async def remove(self, stock_item_id: int, tenant_id: str) -> None:
        await self._collection.delete_one(
            {"stock_item_id": stock_item_id, "tenant_id": tenant_id}
        )
