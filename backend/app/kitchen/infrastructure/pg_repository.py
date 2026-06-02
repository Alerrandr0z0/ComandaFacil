from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from app.kitchen.domain.kitchen_item import KitchenOrder_Item
from app.kitchen.domain.kitchen_station import Beverage, Grill, KitchenStation
from app.kitchen.domain.repository import KitchenOrderItemRepository, KitchenStationRepository
from app.kitchen.domain.states import Cancelled, Preparing, Ready, Waiting
from app.kitchen.infrastructure.orm_models import (
    BeverageORM,
    GrillORM,
    KitchenOrderItemORM,
    KitchenStationORM,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class SQLAlchemyKitchenOrderItemRepository(KitchenOrderItemRepository):
    """SQLAlchemy implementation of KitchenOrderItemRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_id(self, id: int, tenant_id: str) -> KitchenOrder_Item | None:
        stmt = select(KitchenOrderItemORM).where(
            KitchenOrderItemORM.id == id, KitchenOrderItemORM.tenant_id == tenant_id
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if not orm:
            return None
        return self._map_to_domain(orm)

    async def find_by_correlation(
        self, correlation_id: int, tenant_id: str
    ) -> KitchenOrder_Item | None:
        stmt = select(KitchenOrderItemORM).where(
            KitchenOrderItemORM.correlation_id == correlation_id,
            KitchenOrderItemORM.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if not orm:
            return None
        return self._map_to_domain(orm)

    async def find_by_station(self, station_type: str, tenant_id: str) -> list[KitchenOrder_Item]:
        stmt = select(KitchenOrderItemORM).where(
            KitchenOrderItemORM.station_type_cpy == station_type,
            KitchenOrderItemORM.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        orms = result.scalars().all()
        return [self._map_to_domain(o) for o in orms]

    async def save(self, item: KitchenOrder_Item) -> None:
        stmt = select(KitchenOrderItemORM).where(KitchenOrderItemORM.id == item.id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm:
            orm.correlation_id = item.correlation_id
            orm.name_cpy = item.name_cpy
            orm.station_type_cpy = item.station_type_cpy
            orm.tenant_id = item.tenant_id
            orm.state = item.state.name
        else:
            orm = KitchenOrderItemORM(
                id=item.id,
                correlation_id=item.correlation_id,
                name_cpy=item.name_cpy,
                station_type_cpy=item.station_type_cpy,
                tenant_id=item.tenant_id,
                state=item.state.name,
            )
            self._session.add(orm)

        await self._session.flush()

    def _map_to_domain(self, orm: KitchenOrderItemORM) -> KitchenOrder_Item:
        item = KitchenOrder_Item(
            id=orm.id,
            correlation_id=orm.correlation_id,
            name_cpy=orm.name_cpy,
            station_type_cpy=orm.station_type_cpy,
            tenant_id=orm.tenant_id,
        )
        # Map state string back to pure domain state objects
        state_map = {
            "WAITING": Waiting(),
            "PREPARING": Preparing(),
            "READY": Ready(),
            "CANCELLED": Cancelled(),
        }
        item._state = state_map.get(orm.state, Waiting())  # type: ignore[reportPrivateUsage]
        return item


class SQLAlchemyKitchenStationRepository(KitchenStationRepository):
    """SQLAlchemy implementation of KitchenStationRepository using Single Table Inheritance."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_type(self, tenant_id: str, station_type: str) -> list[KitchenStation]:
        stmt = select(KitchenStationORM).where(
            KitchenStationORM.tenant_id == tenant_id,
            KitchenStationORM.station_type == station_type,
        )
        result = await self._session.execute(stmt)
        orms = result.scalars().all()
        return [self._map_to_domain(o) for o in orms]

    async def save(self, station: KitchenStation) -> None:
        stmt = select(KitchenStationORM).where(KitchenStationORM.id == station.id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm:
            orm.tenant_id = station.tenant_id
            orm.is_active = station.is_active
        else:
            if isinstance(station, Grill):
                orm = GrillORM(
                    id=station.id,
                    tenant_id=station.tenant_id,
                    is_active=station.is_active,
                )
            elif isinstance(station, Beverage):
                orm = BeverageORM(
                    id=station.id,
                    tenant_id=station.tenant_id,
                    is_active=station.is_active,
                )
            else:
                raise ValueError(f"Unknown kitchen station class: {station}")
            self._session.add(orm)

        await self._session.flush()

    def _map_to_domain(self, orm: KitchenStationORM) -> KitchenStation:
        if isinstance(orm, GrillORM) or orm.station_type == "GRILL":
            return Grill(id=orm.id, tenant_id=orm.tenant_id, is_active=orm.is_active)
        if isinstance(orm, BeverageORM) or orm.station_type == "BEVERAGE":
            return Beverage(id=orm.id, tenant_id=orm.tenant_id, is_active=orm.is_active)
        raise ValueError(f"Unsupported polymorphic ORM mapper type: {orm}")
