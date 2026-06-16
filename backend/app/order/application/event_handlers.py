from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from app.kitchen.infrastructure.orm_models import KitchenOrderItemORM
from app.order.domain.enums import OrderItemStatus
from app.order.infrastructure.pg_repository import SQLAlchemyOrderRepository
from app.shared import database

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
                await self._process_event(repo, session, event)
            except Exception as e:
                logger.error(
                    f"Failed to sync order item status for KDS event {event}: {e}", exc_info=True
                )

    async def _process_event(
        self,
        repo: SQLAlchemyOrderRepository,
        session: database.AsyncSession,
        event: KitchenItemStatusChanged,
    ) -> None:
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
            logger.warning("Order item %s not found in order %s", event.correlation_id, order.id)
            return

        state_map = {
            "PREPARING": OrderItemStatus.PREPARING,
            "READY": OrderItemStatus.READY,
            "CANCELLED": OrderItemStatus.CANCELED,
            "SURPLUS": OrderItemStatus.CANCELED,
        }
        new_status = state_map.get(event.new_state)
        if new_status:
            if event.new_state in ("CANCELLED", "SURPLUS"):
                await self._sync_cancelled_qty(item, event, session)
            else:
                item.status = new_status

            await repo.save(order)
            await session.commit()
            await self._sync_to_mongo(order)

    async def _sync_cancelled_qty(
        self, item: Any, event: KitchenItemStatusChanged, session: database.AsyncSession
    ) -> None:
        stmt = select(KitchenOrderItemORM).where(
            KitchenOrderItemORM.correlation_id == event.correlation_id,
            KitchenOrderItemORM.tenant_id == event.tenant_id,
            KitchenOrderItemORM.state.in_(["CANCELLED", "SURPLUS"]),
        )
        result = await session.execute(stmt)
        kds_cancelled = len(result.scalars().all())

        diff = kds_cancelled - item.canceled_quantity
        if diff > 0:
            item.cancel_quantity(diff)

    async def _sync_to_mongo(self, order: Any) -> None:
        try:
            mongo = database.get_mongo_db()
        except RuntimeError:
            mongo = None

        if mongo is not None:
            from app.order.infrastructure.order_read_sync import OrderReadModelSync  # noqa: PLC0415

            sync = OrderReadModelSync(mongo)
            await sync.sync(order)


def register_order_listeners() -> None:
    from app.kitchen.domain.kitchen_events import KitchenItemStatusChanged  # noqa: PLC0415
    from app.shared.domain_events import EventBus  # noqa: PLC0415

    EventBus.register(KitchenItemStatusChanged, OrderFormItemStatusListener())
