from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any

from app.order.domain.fulfillment import Delivery, Table, Takeaway

if TYPE_CHECKING:
    from app.order.domain.order_form import OrderForm


class OrderHistoryMongoRepository:
    """Saves closed/completed orders to MongoDB for high-performance read history."""

    def __init__(self, mongo_db: Any) -> None:
        self._collection = mongo_db["order_history"]

    async def save(self, order: OrderForm) -> None:
        """Persists a closed/completed order read model to MongoDB."""
        fulfillment_data: dict[str, Any] = {
            "type": None,
            "fee": "0.00",
        }

        strat = order.fulfillment_strategy
        if strat is not None:
            fulfillment_data["type"] = strat.name
            fulfillment_data["fee"] = str(strat.calculate_fee().amount)

            if isinstance(strat, Table):
                fulfillment_data["table"] = {
                    "table_number": strat.table_num,
                }
            elif isinstance(strat, Takeaway):
                fulfillment_data["takeaway"] = {
                    "customer_name": strat.customer_name,
                }
            elif isinstance(strat, Delivery):
                fulfillment_data["delivery"] = {
                    "street": strat.address.street,
                    "number": strat.address.number,
                    "neighborhood": strat.address.neighborhood,
                    "city": strat.address.city,
                    "state": strat.address.state,
                    "postal_code": strat.address.postal_code,
                    "estimated_time": strat.estimated_time,
                    "tracking_code": strat.tracking_code,
                    "delivery_state": strat.state.name,
                }

        doc = {
            "order_id": order.id,
            "tenant_id": order.tenant_id,
            "total": str(order.total().amount),
            "state": order.state.name,
            "fulfillment": fulfillment_data,
            "items": [
                {
                    "id": item.id,
                    "menu_item_id": item.menu_item_id,
                    "name": item.name_cpy,
                    "price": str(item.price_cpy.amount),
                    "station_type": item.station_type_cpy,
                    "quantity": item.quantity,
                    "notes": item.notes,
                    "subtotal": str(item.calculate_subtotal().amount),
                }
                for item in order.items
            ],
            "closed_at": datetime.datetime.now(datetime.UTC).isoformat(),
        }

        await self._collection.replace_one(
            {"order_id": order.id},
            doc,
            upsert=True,
        )

    async def find_by_id(self, order_id: int, tenant_id: str) -> dict[str, Any] | None:
        """Finds a completed order document by order_id scoped to a tenant."""
        res = await self._collection.find_one(
            {"order_id": order_id, "tenant_id": tenant_id}, {"_id": 0}
        )
        return res if res else None

    async def find_all_by_tenant(self, tenant_id: str) -> list[dict[str, Any]]:
        """Finds all completed order documents for a tenant."""
        cursor = self._collection.find({"tenant_id": tenant_id}, {"_id": 0})
        res = await cursor.to_list(length=100)
        return list(res)
