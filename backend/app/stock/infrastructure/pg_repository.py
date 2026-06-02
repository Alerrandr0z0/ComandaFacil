from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from app.shared.value_objects import MeasuredQuantity, MeasurementUnit
from app.stock.domain.enums import MovementType
from app.stock.domain.stock_item import StockItem
from app.stock.domain.stock_movement import StockMovement
from app.stock.infrastructure.orm_models import StockItemORM, StockMovementORM

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession


class SQLAlchemyStockItemRepository:
    """SQLAlchemy implementation of StockItemRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_id(self, id: int, tenant_id: str) -> StockItem | None:
        stmt = (
            select(StockItemORM)
            .where(StockItemORM.id == id, StockItemORM.tenant_id == tenant_id)
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if not orm:
            return None
        return self._map_to_domain(orm)

    async def find_by_name(self, name: str, tenant_id: str) -> StockItem | None:
        stmt = (
            select(StockItemORM)
            .where(StockItemORM.name == name, StockItemORM.tenant_id == tenant_id)
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if not orm:
            return None
        return self._map_to_domain(orm)

    async def find_all(self, tenant_id: str) -> list[StockItem]:
        stmt = (
            select(StockItemORM)
            .where(StockItemORM.tenant_id == tenant_id)
            .order_by(StockItemORM.name)
        )
        result = await self._session.execute(stmt)
        orms: Sequence[StockItemORM] = result.scalars().all()
        return [self._map_to_domain(o) for o in orms]

    async def find_low_stock(self, tenant_id: str) -> list[StockItem]:
        stmt = (
            select(StockItemORM)
            .where(
                StockItemORM.tenant_id == tenant_id,
                StockItemORM.current_quantity_amount < StockItemORM.min_stock_level,
            )
            .order_by(StockItemORM.name)
        )
        result = await self._session.execute(stmt)
        orms: Sequence[StockItemORM] = result.scalars().all()
        return [self._map_to_domain(o) for o in orms]

    async def save(self, item: StockItem) -> None:
        stmt = select(StockItemORM).where(StockItemORM.id == item.id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm:
            orm.name = item.name
            orm.category = item.category
            orm.current_quantity_amount = item.current_quantity.amount
            orm.current_quantity_unit = item.current_quantity.unit.value
            orm.min_stock_level = item.min_stock_level
            orm.is_active = item.is_active
        else:
            orm = StockItemORM(
                id=item.id,
                tenant_id=item.tenant_id,
                name=item.name,
                category=item.category,
                current_quantity_amount=item.current_quantity.amount,
                current_quantity_unit=item.current_quantity.unit.value,
                min_stock_level=item.min_stock_level,
                is_active=item.is_active,
            )
            self._session.add(orm)

        await self._session.flush()

    async def delete(self, id: int, tenant_id: str) -> None:
        stmt = (
            select(StockItemORM)
            .where(StockItemORM.id == id, StockItemORM.tenant_id == tenant_id)
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm:
            await self._session.delete(orm)
            await self._session.flush()

    @staticmethod
    def _map_to_domain(orm: StockItemORM) -> StockItem:
        return StockItem(
            id=orm.id,
            tenant_id=orm.tenant_id,
            name=orm.name,
            category=orm.category,
            current_quantity=MeasuredQuantity(
                orm.current_quantity_amount,
                MeasurementUnit(orm.current_quantity_unit),
            ),
            min_stock_level=orm.min_stock_level,
            is_active=orm.is_active,
        )


class SQLAlchemyStockMovementRepository:
    """SQLAlchemy implementation of StockMovementRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_stock_item(
        self, stock_item_id: int, tenant_id: str
    ) -> list[StockMovement]:
        stmt = (
            select(StockMovementORM)
            .join(
                StockItemORM,
                StockMovementORM.stock_item_id == StockItemORM.id,
            )
            .where(
                StockItemORM.id == stock_item_id,
                StockItemORM.tenant_id == tenant_id,
            )
            .order_by(StockMovementORM.created_at.desc())
        )
        result = await self._session.execute(stmt)
        orms: Sequence[StockMovementORM] = result.scalars().all()
        return [self._map_to_domain(o) for o in orms]

    async def save(self, movement: StockMovement) -> None:
        orm = StockMovementORM(
            stock_item_id=movement.stock_item_id,
            movement_type=movement.movement_type.value,
            quantity_changed=movement.quantity_changed,
            reason=movement.reason,
            reference_type=movement.reference_type,
            reference_id=movement.reference_id,
            created_at=movement.created_at,
        )
        self._session.add(orm)
        await self._session.flush()

    @staticmethod
    def _map_to_domain(orm: StockMovementORM) -> StockMovement:
        return StockMovement(
            id=orm.id,
            stock_item_id=orm.stock_item_id,
            movement_type=MovementType(orm.movement_type),
            quantity_changed=orm.quantity_changed,
            reason=orm.reason,
            reference_type=orm.reference_type,
            reference_id=orm.reference_id,
            created_at=orm.created_at,
        )
