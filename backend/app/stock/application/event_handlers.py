from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.order.infrastructure.orm_models import OrderFormItemORM
from app.shared import database
from app.stock.application.commands import StockService
from app.stock.infrastructure.pg_repository import (
    SQLAlchemyRecipeRepository,
    SQLAlchemyStockItemRepository,
)

if TYPE_CHECKING:
    from app.kitchen.domain.kitchen_events import KitchenItemStatusChanged

logger = logging.getLogger("app.stock.event_handlers")


class StockDeductionListener:
    async def __call__(self, event: KitchenItemStatusChanged) -> None:
        if event.new_state != "READY":
            return
        if event.old_state == "SURPLUS":
            logger.info(
                "Skipping stock deduction for reclaimed surplus item %s (%s)",
                event.item_id,
                event.name,
            )
            return

        if database.session_factory is None:
            logger.warning("session_factory is None, skipping stock deduction")
            return

        async with database.session_factory() as session:
            try:
                await self._deduct_and_sync(session, event)
            except Exception as e:
                logger.error(
                    f"Failed to deduct stock for KDS completion event {event}: {e}",
                    exc_info=True,
                )

    async def _deduct_and_sync(
        self, session: database.AsyncSession, event: KitchenItemStatusChanged
    ) -> None:
        # 1. Resolve menu_item_id from the order item matching correlation_id
        stmt = select(OrderFormItemORM.menu_item_id).where(
            OrderFormItemORM.id == event.correlation_id
        )
        res = await session.execute(stmt)
        menu_item_id = res.scalar_one_or_none()
        if not menu_item_id:
            logger.warning(
                "Order item %s menu_item_id not found. Cannot deduct stock.",
                event.correlation_id,
            )
            return

        # 2. Instantiate repos and service to run the deduction
        item_repo = SQLAlchemyStockItemRepository(session)
        recipe_repo = SQLAlchemyRecipeRepository(session, item_repo)
        stock_service = StockService(item_repo, recipe_repo)

        # 3. Deduct stock and commit changes
        await stock_service.deduct_by_recipe(menu_item_id, event.tenant_id)
        await session.commit()

        # 4. Synchronize MongoDB read models
        try:
            mongo = database.get_mongo_db()
        except RuntimeError:
            mongo = None

        if mongo is not None:
            from app.stock.infrastructure.stock_read_sync import StockReadModelSync  # noqa: PLC0415

            recipe = await recipe_repo.find_by_menu_item(menu_item_id, event.tenant_id)
            if recipe:
                sync = StockReadModelSync(mongo)
                for ing in recipe.get_ingredients():
                    item = await item_repo.find_by_id(ing.stock_item.id, event.tenant_id)
                    if item:
                        await sync.sync(item)


def register_stock_listeners() -> None:
    from app.kitchen.domain.kitchen_events import KitchenItemStatusChanged  # noqa: PLC0415
    from app.shared.domain_events import EventBus  # noqa: PLC0415

    EventBus.register(KitchenItemStatusChanged, StockDeductionListener())
