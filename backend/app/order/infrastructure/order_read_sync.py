from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.order.domain.order_form import OrderForm


class OrderReadModelSync:
    """Syncs completed Order aggregate to MongoDB 'orders_read' collection for analytics."""

    def __init__(self, mongo_db: Any) -> None:
        self._collection = mongo_db["orders_read"]

    async def sync(self, order: OrderForm) -> None:
        total = float(order.total().amount)
        # Fix: Use original order creation time to avoid drift in analytics
        created_at = order.created_at

        doc: dict[str, Any] = {
            "order_id": order.id,
            "tenant_id": order.tenant_id,
            "display_code": order.display_code,
            "total": total,
            "items": [
                {
                    "id": item.id,
                    "menu_item_id": item.menu_item_id,
                    "name": item.name_cpy,
                    "category": item.station_type_cpy,
                    "price": float(item.price_cpy.amount),
                    # Fix: Handle cancelled items by setting quantity to 0 or deducting cancellations
                    # (Here we use the effective quantity contributing to the subtotal)
                    "quantity": 0 if item.status.value == "CANCELED" else item.quantity,
                    "subtotal": float(item.calculate_subtotal().amount),
                }
                for item in order.items
            ],
            "created_at": created_at,
        }

        await self._collection.replace_one(
            {"order_id": order.id, "tenant_id": order.tenant_id},
            doc,
            upsert=True,
        )
