from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.menu.domain.category import Category, CategoryItem
from app.menu.domain.menu import (
    Menu,
    MenuItem,
    MenuItemRepository,
    MenuRepository,
    PreparationProfile,
)
from app.menu.domain.price_list import PriceList, PriceListItem, PriceListRepository
from app.menu.infrastructure.orm_models import (
    CategoryItemORM,
    MenuItemORM,
    MenuORM,
    PriceListItemORM,
    PriceListORM,
)
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
            .options(selectinload(MenuORM.category_items))
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
            .options(selectinload(MenuORM.category_items))
        )
        result = await self._session.execute(stmt)
        orms = result.scalars().all()
        return [self._map_to_domain(o) for o in orms]

    async def save(self, menu: Menu) -> None:
        stmt = (
            select(MenuORM)
            .where(MenuORM.id == menu.id, MenuORM.tenant_id == menu.tenant_id)
            .options(selectinload(MenuORM.category_items))
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm:
            orm.name = menu.name
            orm.description = menu.description
            orm.is_active = menu.is_active
            orm.active_price_list_id = menu.price_list_id
            orm.category_items.clear()
        else:
            orm = MenuORM(
                id=menu.id,
                tenant_id=menu.tenant_id,
                name=menu.name,
                description=menu.description,
                is_active=menu.is_active,
                active_price_list_id=menu.price_list_id,
            )
            self._session.add(orm)

        for category in menu.categories:
            for item in category.items:
                item_orm = CategoryItemORM(
                    menu_id=menu.id,
                    category_name=category.name,
                    menu_item_id=item.menu_item_id,
                )
                orm.category_items.append(item_orm)

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
            price_list_id=orm.active_price_list_id,
        )
        categories_map: dict[str, list[CategoryItem]] = {}
        for item_orm in orm.category_items:
            categories_map.setdefault(item_orm.category_name, []).append(
                CategoryItem(menu_item_id=item_orm.menu_item_id)
            )
        for cat_name, items in categories_map.items():
            menu.categories.append(Category(name=cat_name, items=items))
        return menu


class SQLAlchemyMenuItemRepository(MenuItemRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_id(self, id: int, tenant_id: str) -> MenuItem | None:
        stmt = select(MenuItemORM).where(MenuItemORM.id == id, MenuItemORM.tenant_id == tenant_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if not orm:
            return None
        return self._map_to_domain(orm)

    async def find_all(self, tenant_id: str) -> list[MenuItem]:
        stmt = select(MenuItemORM).where(MenuItemORM.tenant_id == tenant_id)
        result = await self._session.execute(stmt)
        orms = result.scalars().all()
        return [self._map_to_domain(o) for o in orms]

    async def save(self, item: MenuItem) -> None:
        stmt = select(MenuItemORM).where(
            MenuItemORM.id == item.id, MenuItemORM.tenant_id == item.tenant_id
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm:
            orm.name = item.name
            orm.description = item.description
            orm.base_price = item.base_price.amount
            orm.station_type = item.station_type
            orm.category_name = item.category_name
            orm.image_url = item.image_url
            orm.is_available = item.is_available
            orm.preparation_profile = item.preparation_profile.value
        else:
            orm = MenuItemORM(
                id=item.id,
                tenant_id=item.tenant_id,
                name=item.name,
                description=item.description,
                base_price=item.base_price.amount,
                station_type=item.station_type,
                category_name=item.category_name,
                image_url=item.image_url,
                is_available=item.is_available,
                preparation_profile=item.preparation_profile.value,
            )
            self._session.add(orm)
        await self._session.flush()

    async def delete(self, id: int, tenant_id: str) -> None:
        stmt = select(MenuItemORM).where(MenuItemORM.id == id, MenuItemORM.tenant_id == tenant_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm:
            await self._session.delete(orm)
            await self._session.flush()

    def _map_to_domain(self, orm: MenuItemORM) -> MenuItem:
        return MenuItem(
            id=orm.id,
            tenant_id=orm.tenant_id,
            name=orm.name,
            description=orm.description,
            base_price=Money(amount=orm.base_price),
            station_type=orm.station_type,
            category_name=orm.category_name,
            image_url=orm.image_url,
            is_available=orm.is_available,
            preparation_profile=PreparationProfile(orm.preparation_profile),
        )


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
                menu_id=price_list.menu_id,
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
        stmt = select(PriceListORM).where(
            PriceListORM.id == id, PriceListORM.tenant_id == tenant_id
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm:
            await self._session.delete(orm)
            await self._session.flush()

    async def find_by_menu_id(self, menu_id: int, tenant_id: str) -> list[PriceList]:
        stmt = (
            select(PriceListORM)
            .options(selectinload(PriceListORM.items))
            .where(
                PriceListORM.menu_id == menu_id,
                PriceListORM.tenant_id == tenant_id,
            )
            .order_by(PriceListORM.id)
        )
        result = await self._session.execute(stmt)
        orms = result.scalars().all()
        return [self._map_to_domain(orm) for orm in orms]

    def _map_to_domain(self, orm: PriceListORM) -> PriceList:
        pl = PriceList(
            id=orm.id,
            tenant_id=orm.tenant_id,
            menu_id=orm.menu_id,
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
