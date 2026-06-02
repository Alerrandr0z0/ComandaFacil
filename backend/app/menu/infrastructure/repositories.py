from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.menu.domain.category import Category
from app.menu.domain.menu import Menu, MenuItem, MenuRepository
from app.menu.domain.price_list import PriceList, PriceListItem, PriceListRepository
from app.menu.infrastructure.orm_models import MenuItemORM, MenuORM, PriceListItemORM, PriceListORM
from app.shared.money import Money

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class SQLAlchemyMenuRepository(MenuRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_id(self, id: int, tenant_id: str) -> Menu | None:
        stmt = (
            select(MenuORM)
            .where(MenuORM.id == id, MenuORM.tenant_id == tenant_id)
            .options(selectinload(MenuORM.items))
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if not orm:
            return None
        return self._map_to_domain(orm)

    async def find_all(self, tenant_id: str) -> list[Menu]:
        stmt = (
            select(MenuORM)
            .where(MenuORM.tenant_id == tenant_id)
            .options(selectinload(MenuORM.items))
        )
        result = await self._session.execute(stmt)
        orms = result.scalars().all()
        return [self._map_to_domain(o) for o in orms]

    async def save(self, menu: Menu) -> None:
        stmt = (
            select(MenuORM)
            .where(MenuORM.id == menu.id, MenuORM.tenant_id == menu.tenant_id)
            .options(selectinload(MenuORM.items))
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm:
            orm.name = menu.name
            orm.description = menu.description
            orm.is_active = menu.is_active
            orm.items.clear()
        else:
            orm = MenuORM(
                id=menu.id,
                tenant_id=menu.tenant_id,
                name=menu.name,
                description=menu.description,
                is_active=menu.is_active,
            )
            self._session.add(orm)

        for item in menu.items:
            item_orm = MenuItemORM(
                id=item.id,
                menu_id=menu.id,
                name=item.name,
                description=item.description,
                category=str(item.category),
                image_url=item.image_url,
                is_available=item.is_available,
            )
            orm.items.append(item_orm)

        await self._session.flush()

    async def delete(self, id: int, tenant_id: str) -> None:
        stmt = select(MenuORM).where(MenuORM.id == id, MenuORM.tenant_id == tenant_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm:
            await self._session.delete(orm)
            await self._session.flush()

    def _map_to_domain(self, orm: MenuORM) -> Menu:
        menu = Menu(
            id=orm.id,
            tenant_id=orm.tenant_id,
            name=orm.name,
            description=orm.description,
            is_active=orm.is_active,
        )
        for item_orm in orm.items:
            item = MenuItem(
                id=item_orm.id,
                name=item_orm.name,
                description=item_orm.description,
                category=Category(item_orm.category),
                image_url=item_orm.image_url,
                is_available=item_orm.is_available,
            )
            menu.items.append(item)
        return menu


class SQLAlchemyPriceListRepository(PriceListRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_id(self, id: int, tenant_id: str) -> PriceList | None:
        stmt = (
            select(PriceListORM)
            .where(PriceListORM.id == id, PriceListORM.tenant_id == tenant_id)
            .options(selectinload(PriceListORM.items))
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if not orm:
            return None
        return self._map_to_domain(orm)

    async def find_active(self, tenant_id: str) -> list[PriceList]:
        stmt = (
            select(PriceListORM)
            .where(PriceListORM.is_active.is_(True), PriceListORM.tenant_id == tenant_id)
            .options(selectinload(PriceListORM.items))
        )
        result = await self._session.execute(stmt)
        orms = result.scalars().all()
        return [self._map_to_domain(o) for o in orms]

    async def find_all(self, tenant_id: str) -> list[PriceList]:
        stmt = (
            select(PriceListORM)
            .where(PriceListORM.tenant_id == tenant_id)
            .options(selectinload(PriceListORM.items))
        )
        result = await self._session.execute(stmt)
        orms = result.scalars().all()
        return [self._map_to_domain(o) for o in orms]

    async def save(self, price_list: PriceList) -> None:
        stmt = (
            select(PriceListORM)
            .where(PriceListORM.id == price_list.id, PriceListORM.tenant_id == price_list.tenant_id)
            .options(selectinload(PriceListORM.items))
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm:
            orm.name = price_list.name
            orm.description = price_list.description
            orm.is_active = price_list.is_active
            orm.valid_from = price_list.valid_from
            orm.valid_until = price_list.valid_until
            orm.items.clear()
        else:
            orm = PriceListORM(
                id=price_list.id,
                tenant_id=price_list.tenant_id,
                name=price_list.name,
                description=price_list.description,
                is_active=price_list.is_active,
                valid_from=price_list.valid_from,
                valid_until=price_list.valid_until,
            )
            self._session.add(orm)

        for item in price_list.items:
            item_orm = PriceListItemORM(
                id=item.id,
                price_list_id=price_list.id,
                menu_item_id=item.menu_item_id,
                price=item.price.amount,
            )
            orm.items.append(item_orm)

        await self._session.flush()

    async def delete(self, id: int, tenant_id: str) -> None:
        stmt = select(PriceListORM).where(PriceListORM.id == id, PriceListORM.tenant_id == tenant_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm:
            await self._session.delete(orm)
            await self._session.flush()

    def _map_to_domain(self, orm: PriceListORM) -> PriceList:
        pl = PriceList(
            id=orm.id,
            tenant_id=orm.tenant_id,
            name=orm.name,
            description=orm.description,
            is_active=orm.is_active,
            valid_from=orm.valid_from,
            valid_until=orm.valid_until,
        )
        for item_orm in orm.items:
            item = PriceListItem(
                id=item_orm.id,
                price_list_id=orm.id,
                menu_item_id=item_orm.menu_item_id,
                price=Money(amount=item_orm.price),
            )
            pl.items.append(item)
        return pl
