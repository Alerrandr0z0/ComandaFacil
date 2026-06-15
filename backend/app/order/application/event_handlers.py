from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.shared import database
from app.order.infrastructure.pg_repository import SQLAlchemyOrderRepository
from app.order.domain.enums import OrderItemStatus

if TYPE_CHECKING:
    from app.kitchen.domain.kitchen_events import KitchenItemStatusChanged

logger = logging.getLogger("app.order.event_handlers")


class OrderFormItemStatusListener:
    async def __call__(self, event: KitchenItemStatusChanged) -> None:
        if database.session_factory is None:
            logger.warning("session_factory is None, skipping order item status sync")
            return

        async with database.session_factory() as session:
            repo = SQLAlchemyOrderRepository(session)
            try:
                order = await repo.find_by_item_id(event.correlation_id, event.tenant_id)
                if not order:
                    logger.warning(
                        "Order not found for item_id=%s tenant_id=%s",
                        event.correlation_id,
                        event.tenant_id,
                    )
                    return

                item = next((i for i in order.items if i.id == event.correlation_id), None)
                if not item:
                    logger.warning(
                        "Order item %s not found in order %s", event.correlation_id, order.id
                    )
                    return

                state_map = {
                    "PREPARING": OrderItemStatus.PREPARING,
                    "READY": OrderItemStatus.READY,
                    "CANCELLED": OrderItemStatus.CANCELED,
                }
                new_status = state_map.get(event.new_state)
                if new_status:
                    item.status = new_status
                    await repo.save(order)
                    await session.commit()

                    try:
                        mongo = database.get_mongo_db()
                    except RuntimeError:
                        mongo = None

                    if mongo is not None:
                        from app.order.infrastructure.order_read_sync import OrderReadModelSync
                        sync = OrderReadModelSync(mongo)
                        await sync.sync(order)

            except Exception as e:
                logger.error(
                    f"Failed to sync order item status for KDS event {event}: {e}", exc_info=True
                )
