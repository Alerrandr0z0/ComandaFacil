from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from app.menu.domain.menu import Menu, MenuItem, MenuItemRepository, MenuRepository
from app.shared.exceptions import ConflictError, NotFoundError
from app.shared.money import Money


@dataclass(frozen=True)
class CreateMenuCommand:
    id: int
    tenant_id: str
    name: str
    description: str = ""

    def __repr__(self) -> str:
        return f"CreateMenuCommand(id={self.id}, tenant_id={self.tenant_id!r}, name={self.name!r})"


class CreateMenuHandler:
    def __init__(self, menu_repo: MenuRepository) -> None:
        self._menu_repo: Final[MenuRepository] = menu_repo

    async def handle(self, command: CreateMenuCommand) -> Menu:
        existing = await self._menu_repo.find_by_id(command.id, command.tenant_id)
        if existing:
            raise ConflictError(f"Cardápio com id {command.id} já existe.")

        menu = Menu(
            id=command.id,
            tenant_id=command.tenant_id,
            name=command.name,
            description=command.description,
            is_active=True,
        )
        await self._menu_repo.save(menu)
        return menu

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"


@dataclass(frozen=True)
class AddMenuItemCommand:
    menu_id: int
    tenant_id: str
    item_id: int
    name: str
    description: str
    category: str
    base_price: Money | None = None
    station_type: str = "GRILL"
    image_url: str | None = None
    is_available: bool = True

    def __repr__(self) -> str:
        return f"AddMenuItemCommand(menu_id={self.menu_id}, tenant_id={self.tenant_id!r}, item_id={self.item_id}, name={self.name!r})"


class AddMenuItemHandler:
    def __init__(self, menu_repo: MenuRepository, item_repo: MenuItemRepository) -> None:
        self._menu_repo: Final[MenuRepository] = menu_repo
        self._item_repo: Final[MenuItemRepository] = item_repo

    async def handle(self, command: AddMenuItemCommand) -> MenuItem:
        menu = await self._menu_repo.find_by_id(command.menu_id, command.tenant_id)
        if not menu:
            raise NotFoundError("Cardápio", command.menu_id)

        # Create/Save the MenuItem as a standalone aggregate
        base_price = command.base_price or Money.zero()
        item = MenuItem(
            id=command.item_id,
            tenant_id=command.tenant_id,
            name=command.name,
            description=command.description,
            base_price=base_price,
            station_type=command.station_type,
            category_name=command.category,
            image_url=command.image_url,
            is_available=command.is_available,
        )
        await self._item_repo.save(item)

        # Associate the MenuItem to the Menu category
        menu.add_item_to_category(command.category, command.item_id)
        await self._menu_repo.save(menu)
        return item

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"


@dataclass(frozen=True)
class RemoveMenuItemCommand:
    menu_id: int
    tenant_id: str
    item_id: int

    def __repr__(self) -> str:
        return f"RemoveMenuItemCommand(menu_id={self.menu_id}, tenant_id={self.tenant_id!r}, item_id={self.item_id})"


class RemoveMenuItemHandler:
    def __init__(self, menu_repo: MenuRepository) -> None:
        self._menu_repo: Final[MenuRepository] = menu_repo

    async def handle(self, command: RemoveMenuItemCommand) -> None:
        menu = await self._menu_repo.find_by_id(command.menu_id, command.tenant_id)
        if not menu:
            raise NotFoundError("Cardápio", command.menu_id)

        found_category = None
        for category in menu.categories:
            if any(item.menu_item_id == command.item_id for item in category.items):
                found_category = category.name
                break

        if not found_category:
            raise ValueError(f"Item com id {command.item_id} não encontrado neste cardápio.")

        menu.remove_item_from_category(found_category, command.item_id)
        await self._menu_repo.save(menu)

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"


@dataclass(frozen=True)
class ToggleMenuCommand:
    menu_id: int
    tenant_id: str
    activate: bool

    def __repr__(self) -> str:
        return f"ToggleMenuCommand(menu_id={self.menu_id}, tenant_id={self.tenant_id!r}, activate={self.activate})"


class ToggleMenuHandler:
    def __init__(self, menu_repo: MenuRepository) -> None:
        self._menu_repo: Final[MenuRepository] = menu_repo

    async def handle(self, command: ToggleMenuCommand) -> Menu:
        menu = await self._menu_repo.find_by_id(command.menu_id, command.tenant_id)
        if not menu:
            raise NotFoundError("Cardápio", command.menu_id)
        if command.activate:
            menu.activate()
        else:
            menu.deactivate()
        await self._menu_repo.save(menu)
        return menu

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"


@dataclass(frozen=True)
class DeleteMenuCommand:
    menu_id: int
    tenant_id: str

    def __repr__(self) -> str:
        return f"DeleteMenuCommand(menu_id={self.menu_id}, tenant_id={self.tenant_id!r})"


class DeleteMenuHandler:
    def __init__(self, menu_repo: MenuRepository) -> None:
        self._menu_repo: Final[MenuRepository] = menu_repo

    async def handle(self, command: DeleteMenuCommand) -> None:
        menu = await self._menu_repo.find_by_id(command.menu_id, command.tenant_id)
        if not menu:
            raise NotFoundError("Cardápio", command.menu_id)
        await self._menu_repo.delete(command.menu_id, command.tenant_id)

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"


@dataclass(frozen=True)
class AssociatePriceListToMenuCommand:
    menu_id: int
    tenant_id: str
    price_list_id: int | None

    def __repr__(self) -> str:
        return f"AssociatePriceListToMenuCommand(menu_id={self.menu_id}, tenant_id={self.tenant_id!r}, price_list_id={self.price_list_id})"


class AssociatePriceListToMenuHandler:
    def __init__(self, menu_repo: MenuRepository) -> None:
        self._menu_repo: Final[MenuRepository] = menu_repo

    async def handle(self, command: AssociatePriceListToMenuCommand) -> Menu:
        menu = await self._menu_repo.find_by_id(command.menu_id, command.tenant_id)
        if not menu:
            raise NotFoundError("Cardápio", command.menu_id)
        menu.associate_price_list(command.price_list_id)
        await self._menu_repo.save(menu)
        return menu

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"
