from __future__ import annotations

import contextlib
import logging
from typing import TYPE_CHECKING

from sqlalchemy import select, or_

from app.shared import database
from app.menu.infrastructure.repositories import SQLAlchemyMenuItemRepository
from app.kitchen.infrastructure.pg_repository import SQLAlchemyKitchenOrderItemRepository
from app.kitchen.infrastructure.orm_models import KitchenOrderItemORM
from app.kitchen.domain.kitchen_item import KitchenOrderItem
from app.kitchen.infrastructure.websocket_manager import kds_ws_manager
from app.order.infrastructure.orm_models import OrderFormItemORM

if TYPE_CHECKING:
    from app.order.domain.order_events import OrderItemAdded, OrderItemCancelled, OrderCancelled

logger = logging.getLogger("app.kitchen.event_handlers")


class ReceiveKitchenOrderItemListener:
    async def __call__(self, event: OrderItemAdded) -> None:
        if database.session_factory is None:
            logger.warning("session_factory is None, skipping kitchen notification")
            return

        async with database.session_factory() as session:
            item_repo = SQLAlchemyMenuItemRepository(session)
            menu_item = await item_repo.find_by_id(event.menu_item_id, event.tenant_id)
            if not menu_item:
                logger.warning(
                    "Menu item %s not found for tenant %s", event.menu_item_id, event.tenant_id
                )
                return

            kitchen_repo = SQLAlchemyKitchenOrderItemRepository(session)
            try:
                if not event.notes:
                    notes_cond = or_(
                        KitchenOrderItemORM.notes.is_(None),
                        KitchenOrderItemORM.notes == "",
                    )
                else:
                    notes_cond = KitchenOrderItemORM.notes == event.notes

                stmt = (
                    select(KitchenOrderItemORM)
                    .where(
                        KitchenOrderItemORM.state == "SURPLUS",
                        KitchenOrderItemORM.name_cpy == menu_item.name,
                        KitchenOrderItemORM.tenant_id == event.tenant_id,
                        notes_cond,
                    )
                    .order_by(KitchenOrderItemORM.id.asc())
                )
                result = await session.execute(stmt)
                surplus_orms = list(result.scalars().all())

                items_created: list[KitchenOrderItem] = []
                for seq in range(event.quantity):
                    unique_id = event.item_id * 1000 + seq
                    existing = await kitchen_repo.find_by_id(unique_id, event.tenant_id)
                    if existing:
                        items_created.append(existing)
                        continue

                    if surplus_orms:
                        surplus_orm = surplus_orms.pop(0)
                        item = kitchen_repo.map_to_domain(surplus_orm)
                        item.reclaim(event.item_id)
                        item.notes = event.notes
                        await kitchen_repo.save(item)
                        items_created.append(item)

                        await kds_ws_manager.broadcast_to_station(
                            tenant_id=event.tenant_id,
                            station_type=menu_item.station_type,
                            event_data={
                                "event": "ITEM_READY",
                                "item": {
                                    "id": item.id,
                                    "correlation_id": item.correlation_id,
                                    "name_cpy": item.name_cpy,
                                    "station_type_cpy": item.station_type_cpy,
                                    "state": item.state.name,
                                    "notes": item.notes,
                                },
                            },
                        )
                    else:
                        item = KitchenOrderItem(
                            id=unique_id,
                            correlation_id=event.item_id,
                            name_cpy=menu_item.name,
                            station_type_cpy=menu_item.station_type,
                            tenant_id=event.tenant_id,
                            preparation_profile=menu_item.preparation_profile.value,
                            notes=event.notes,
                        )
                        await kitchen_repo.save(item)
                        items_created.append(item)

                        await kds_ws_manager.broadcast_to_station(
                            tenant_id=event.tenant_id,
                            station_type=menu_item.station_type,
                            event_data={
                                "event": "ITEM_RECEIVED",
                                "item": {
                                    "id": item.id,
                                    "correlation_id": item.correlation_id,
                                    "name_cpy": item.name_cpy,
                                    "station_type_cpy": item.station_type_cpy,
                                    "state": item.state.name,
                                    "notes": item.notes,
                                    "menu_item_id": event.menu_item_id,
                                },
                            },
                        )

                await session.commit()

                # Sync to MongoDB read models
                try:
                    mongo = database.get_mongo_db()
                except RuntimeError:
                    mongo = None

                if mongo is not None:
                    from app.kitchen.infrastructure.kitchen_read_sync import KitchenReadModelSync
                    sync = KitchenReadModelSync(mongo)
                    for item in items_created:
                        await sync.sync(item)

            except Exception as e:
                logger.error(f"Failed to receive kitchen order item for event {event}: {e}", exc_info=True)


class CancelKitchenOrderItemListener:
    async def __call__(self, event: OrderItemCancelled | OrderCancelled) -> None:
        if database.session_factory is None:
            logger.warning("session_factory is None, skipping kitchen cancellation")
            return

        from app.order.domain.order_events import OrderCancelled

        async with database.session_factory() as session:
            kitchen_repo = SQLAlchemyKitchenOrderItemRepository(session)
            try:
                # 1. Determine which correlation_ids (order item IDs) to cancel
                if isinstance(event, OrderCancelled):
                    stmt_items = select(OrderFormItemORM.id).where(
                        OrderFormItemORM.order_id == event.order_id
                    )
                    result_items = await session.execute(stmt_items)
                    order_item_ids = list(result_items.scalars().all())
                else:
                    order_item_ids = [event.item_id]

                if not order_item_ids:
                    return

                # 2. Query all corresponding kitchen item ORMs
                stmt = select(KitchenOrderItemORM).where(
                    KitchenOrderItemORM.correlation_id.in_(order_item_ids),
                    KitchenOrderItemORM.tenant_id == event.tenant_id,
                )
                result = await session.execute(stmt)
                orms = list(result.scalars().all())

                items_to_sync: list[KitchenOrderItem] = []
                cancel_ids: list[int] = []

                for orm in orms:
                    kitchen_item = kitchen_repo.map_to_domain(orm)

                    if isinstance(event, OrderCancelled):
                        # For entire comanda cancel: surplus logic or cancel
                        if kitchen_item.state.name == "READY":
                            kitchen_item.cancel()  # Surplus
                            kitchen_item.correlation_id = 0
                            await kitchen_repo.save(kitchen_item)
                            items_to_sync.append(kitchen_item)
                        elif kitchen_item.state.name not in ("CANCELLED", "SURPLUS"):
                            kitchen_item.cancel()  # Cancelled
                            await kitchen_repo.save(kitchen_item)
                            items_to_sync.append(kitchen_item)
                    else:
                        # For single order item cancel: cancel or surplus matching quantity
                        old_state = kitchen_item.state.name
                        if old_state == "READY":
                            kitchen_item.cancel()  # surplus
                            kitchen_item.correlation_id = 0
                            await kitchen_repo.save(kitchen_item)
                            items_to_sync.append(kitchen_item)
                        elif old_state not in ("CANCELLED", "SURPLUS"):
                            kitchen_item.cancel()
                            await kitchen_repo.save(kitchen_item)
                            items_to_sync.append(kitchen_item)
                            cancel_ids.append(kitchen_item.id)

                await session.commit()

                # 3. Synchronize MongoDB read models
                try:
                    mongo = database.get_mongo_db()
                except RuntimeError:
                    mongo = None

                if mongo is not None:
                    # For active cancellations, delete from kitchen_read immediately
                    if cancel_ids:
                        await mongo["kitchen_read"].delete_many(
                            {
                                "kitchen_item_id": {"$in": cancel_ids},
                                "tenant_id": event.tenant_id,
                            }
                        )
                    # For surplus or whole comanda cancellation, sync updated items
                    if isinstance(event, OrderCancelled):
                        await mongo["kitchen_read"].delete_many(
                            {
                                "correlation_id": {"$in": order_item_ids},
                                "tenant_id": event.tenant_id,
                            }
                        )

                    from app.kitchen.infrastructure.kitchen_read_sync import KitchenReadModelSync
                    sync = KitchenReadModelSync(mongo)
                    for k_item in items_to_sync:
                        if k_item.state.name == "SURPLUS":
                            await sync.sync(k_item)

                # 4. Broadcast websocket events
                for k_item in items_to_sync:
                    with contextlib.suppress(Exception):
                        await kds_ws_manager.broadcast_to_station(
                            tenant_id=event.tenant_id,
                            station_type=k_item.station_type_cpy,
                            event_data={
                                "event": "ITEM_CANCELLED",
                                "item": {
                                    "id": k_item.id,
                                    "correlation_id": k_item.correlation_id,
                                    "state": k_item.state.name,
                                },
                            },
                        )

            except Exception as e:
                logger.error(f"Failed to cancel kitchen order items for event {event}: {e}", exc_info=True)
