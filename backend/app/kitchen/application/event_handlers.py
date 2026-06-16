from __future__ import annotations

import contextlib
import logging
from typing import Any

from sqlalchemy import or_, select

from app.kitchen.domain.kitchen_item import KitchenOrderItem
from app.kitchen.infrastructure.kitchen_read_sync import KitchenReadModelSync
from app.kitchen.infrastructure.orm_models import KitchenOrderItemORM
from app.kitchen.infrastructure.pg_repository import SQLAlchemyKitchenOrderItemRepository
from app.kitchen.infrastructure.websocket_manager import kds_ws_manager
from app.menu.infrastructure.repositories import SQLAlchemyMenuItemRepository
from app.order.domain.order_events import (
    OrderCancelled,
    OrderItemAdded,
    OrderItemCancelRequested,
)
from app.order.infrastructure.orm_models import OrderFormItemORM
from app.shared import database
from app.shared.domain_events import EventBus

logger = logging.getLogger("app.kitchen.event_handlers")


class ReceiveKitchenOrderItemListener:
    async def _process_sequence(
        self,
        event: OrderItemAdded,
        kitchen_repo: SQLAlchemyKitchenOrderItemRepository,
        menu_item: Any,
        surplus_orms: list[KitchenOrderItemORM],
    ) -> KitchenOrderItem:
        # We check if this specific item sequence was already processed to avoid duplicates on retry
        # (Though with ID=0, we'll rely on the handler logic to only call this for new items)

        if surplus_orms:
            surplus_orm = surplus_orms.pop(0)
            item = kitchen_repo.map_to_domain(surplus_orm)
            item.reclaim(event.item_id)
            item.notes = event.notes
            await kitchen_repo.save(item)

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
                        "menu_item_id": event.menu_item_id,
                    },
                },
            )
            return item

        item = KitchenOrderItem(
            id=0,  # Let database generate unique ID
            correlation_id=event.item_id,
            name_cpy=menu_item.name,
            station_type_cpy=menu_item.station_type,
            tenant_id=event.tenant_id,
            preparation_profile=menu_item.preparation_profile.value,
            notes=event.notes,
        )
        await kitchen_repo.save(item)

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
        return item

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
                notes_cond = (
                    or_(
                        KitchenOrderItemORM.notes.is_(None),
                        KitchenOrderItemORM.notes == "",
                    )
                    if not event.notes
                    else KitchenOrderItemORM.notes == event.notes
                )

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
                for _ in range(event.quantity):
                    item = await self._process_sequence(
                        event, kitchen_repo, menu_item, surplus_orms
                    )
                    items_created.append(item)

                await session.commit()

                # Sync to MongoDB read models
                try:
                    mongo = database.get_mongo_db()
                except RuntimeError:
                    mongo = None

                if mongo is not None:
                    sync = KitchenReadModelSync(mongo)
                    for item in items_created:
                        await sync.sync(item, menu_item_id=menu_item.id)

            except Exception as e:
                logger.error(
                    f"Failed to receive kitchen order item for event {event}: {e}", exc_info=True
                )


class CancelKitchenOrderItemListener:
    async def _get_order_item_ids(
        self, event: OrderItemCancelRequested | OrderCancelled, session: database.AsyncSession
    ) -> list[int]:
        if isinstance(event, OrderCancelled):
            stmt_items = select(OrderFormItemORM.id).where(
                OrderFormItemORM.order_id == event.order_id
            )
            result_items = await session.execute(stmt_items)
            return list(result_items.scalars().all())
        return [event.item_id]

    async def _process_orms_to_cancel(
        self,
        event: OrderItemCancelRequested | OrderCancelled,
        orms: list[KitchenOrderItemORM],
        kitchen_repo: SQLAlchemyKitchenOrderItemRepository,
    ) -> tuple[list[KitchenOrderItem], list[int]]:
        items_to_sync: list[KitchenOrderItem] = []
        delete_ids: list[int] = []

        if isinstance(event, OrderCancelled):
            target_orms = orms
        else:
            state_priority = {"WAITING": 0, "PREPARING": 1, "READY": 2}
            orms.sort(key=lambda o: state_priority.get(o.state, 99))
            target_orms = orms[: event.quantity]

        for orm in target_orms:
            kitchen_item = kitchen_repo.map_to_domain(orm)
            old_state = kitchen_item.state.name
            if old_state == "WAITING":
                kitchen_item.cancel()
                await kitchen_repo.save(kitchen_item)
                delete_ids.append(kitchen_item.id)
            elif old_state in ("PREPARING", "READY"):
                kitchen_item.cancel()
                await kitchen_repo.save(kitchen_item)
                items_to_sync.append(kitchen_item)

        return items_to_sync, delete_ids

    async def __call__(self, event: OrderItemCancelRequested | OrderCancelled) -> None:
        if database.session_factory is None:
            logger.warning("session_factory is None, skipping kitchen cancellation")
            return

        async with database.session_factory() as session:
            kitchen_repo = SQLAlchemyKitchenOrderItemRepository(session)
            try:
                order_item_ids = await self._get_order_item_ids(event, session)
                if not order_item_ids:
                    return

                stmt = select(KitchenOrderItemORM).where(
                    KitchenOrderItemORM.correlation_id.in_(order_item_ids),
                    KitchenOrderItemORM.tenant_id == event.tenant_id,
                )
                result = await session.execute(stmt)
                orms = list(result.scalars().all())

                items_to_sync, delete_ids = await self._process_orms_to_cancel(
                    event, orms, kitchen_repo
                )

                await session.commit()

                # Synchronize MongoDB read models
                try:
                    mongo = database.get_mongo_db()
                except RuntimeError:
                    mongo = None

                if mongo is not None:
                    if delete_ids:
                        await mongo["kitchen_read"].delete_many(
                            {
                                "kitchen_item_id": {"$in": delete_ids},
                                "tenant_id": event.tenant_id,
                            }
                        )
                    sync = KitchenReadModelSync(mongo)
                    for k_item in items_to_sync:
                        await sync.sync(k_item)

                # Broadcast websocket events
                for k_item in items_to_sync:
                    with contextlib.suppress(Exception):
                        await kds_ws_manager.broadcast_to_station(
                            tenant_id=event.tenant_id,
                            station_type=k_item.station_type_cpy,
                            event_data={
                                "event": "ITEM_CANCEL_REQUESTED",
                                "item": {
                                    "id": k_item.id,
                                    "correlation_id": k_item.correlation_id,
                                    "state": k_item.state.name,
                                },
                            },
                        )

            except Exception as e:
                logger.error(
                    f"Failed to cancel kitchen order items for event {event}: {e}", exc_info=True
                )


def register_kitchen_listeners() -> None:
    EventBus.register(OrderItemAdded, ReceiveKitchenOrderItemListener())
    EventBus.register(OrderItemCancelRequested, CancelKitchenOrderItemListener())
    EventBus.register(OrderCancelled, CancelKitchenOrderItemListener())
