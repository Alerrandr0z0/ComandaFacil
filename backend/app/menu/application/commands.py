from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from datetime import datetime as _dt

from app.menu.domain.menu import (
    Menu,
    MenuItem,
    MenuItemRepository,
    MenuRepository,
    PreparationProfile,
)
from app.menu.domain.price_list import PriceList, PriceListItem, PriceListRepository
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
    preparation_profile: PreparationProfile = PreparationProfile.STANDARD

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
            preparation_profile=command.preparation_profile,
        )
        await self._item_repo.save(item)

        # Associate the MenuItem to the Menu category
        menu.add_item_to_category(command.category, command.item_id)
        await self._menu_repo.save(menu)
        return item

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"


@dataclass(frozen=True)
class LinkMenuItemCommand:
    menu_id: int
    tenant_id: str
    item_id: int
    category: str

    def __repr__(self) -> str:
        return (
            f"LinkMenuItemCommand(menu_id={self.menu_id}, "
            f"tenant_id={self.tenant_id!r}, item_id={self.item_id}, "
            f"category={self.category!r})"
        )


class LinkMenuItemHandler:
    def __init__(self, menu_repo: MenuRepository, item_repo: MenuItemRepository) -> None:
        self._menu_repo: Final[MenuRepository] = menu_repo
        self._item_repo: Final[MenuItemRepository] = item_repo

    async def handle(self, command: LinkMenuItemCommand) -> MenuItem:
        menu = await self._menu_repo.find_by_id(command.menu_id, command.tenant_id)
        if not menu:
            raise NotFoundError("Cardápio", command.menu_id)

        item = await self._item_repo.find_by_id(command.item_id, command.tenant_id)
        if not item:
            raise NotFoundError("MenuItem", command.item_id)

        try:
            menu.add_item_to_category(command.category, command.item_id)
        except ValueError as e:
            raise ConflictError(str(e)) from e

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
class CreateCatalogItemCommand:
    id: int
    tenant_id: str
    name: str
    description: str = ""
    category: str = ""
    base_price: Money | None = None
    station_type: str = "GRILL"
    image_url: str | None = None
    is_available: bool = True
    preparation_profile: PreparationProfile = PreparationProfile.STANDARD

    def __repr__(self) -> str:
        return f"CreateCatalogItemCommand(id={self.id}, tenant_id={self.tenant_id!r}, name={self.name!r})"


class CreateCatalogItemHandler:
    def __init__(self, item_repo: MenuItemRepository) -> None:
        self._item_repo: Final[MenuItemRepository] = item_repo

    async def handle(self, command: CreateCatalogItemCommand) -> MenuItem:
        base_price = command.base_price or Money.zero()
        item = MenuItem(
            id=command.id,
            tenant_id=command.tenant_id,
            name=command.name,
            description=command.description,
            base_price=base_price,
            station_type=command.station_type,
            category_name=command.category,
            image_url=command.image_url,
            is_available=command.is_available,
            preparation_profile=command.preparation_profile,
        )
        await self._item_repo.save(item)
        return item

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"


@dataclass(frozen=True)
class UpdateCatalogItemCommand:
    item_id: int
    tenant_id: str
    name: str
    description: str
    category: str
    base_price: Money
    station_type: str
    image_url: str | None
    is_available: bool

    def __repr__(self) -> str:
        return f"UpdateCatalogItemCommand(item_id={self.item_id}, tenant_id={self.tenant_id!r}, name={self.name!r})"


class UpdateCatalogItemHandler:
    def __init__(self, item_repo: MenuItemRepository) -> None:
        self._item_repo: Final[MenuItemRepository] = item_repo

    async def handle(self, command: UpdateCatalogItemCommand) -> MenuItem:
        item = await self._item_repo.find_by_id(command.item_id, command.tenant_id)
        if not item:
            raise NotFoundError("MenuItem", command.item_id)
        item.update_details(
            name=command.name,
            description=command.description,
            base_price=command.base_price,
            station_type=command.station_type,
            category_name=command.category,
            image_url=command.image_url,
        )
        item.update_availability(command.is_available)
        await self._item_repo.save(item)
        return item

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"


@dataclass(frozen=True)
class DeleteCatalogItemCommand:
    item_id: int
    tenant_id: str

    def __repr__(self) -> str:
        return f"DeleteCatalogItemCommand(item_id={self.item_id}, tenant_id={self.tenant_id!r})"


class DeleteCatalogItemHandler:
    def __init__(self, item_repo: MenuItemRepository) -> None:
        self._item_repo: Final[MenuItemRepository] = item_repo

    async def handle(self, command: DeleteCatalogItemCommand) -> None:
        item = await self._item_repo.find_by_id(command.item_id, command.tenant_id)
        if not item:
            raise NotFoundError("MenuItem", command.item_id)
        await self._item_repo.delete(command.item_id, command.tenant_id)

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


@dataclass(frozen=True)
class CreatePriceListCommand:
    id: int
    tenant_id: str
    menu_id: int
    name: str
    description: str = ""
    is_active: bool = True
    valid_from: _dt | None = None
    valid_until: _dt | None = None

    def __repr__(self) -> str:
        return f"CreatePriceListCommand(id={self.id}, tenant_id={self.tenant_id!r}, menu_id={self.menu_id}, name={self.name!r})"


class CreatePriceListHandler:
    def __init__(self, price_list_repo: PriceListRepository) -> None:
        self._price_list_repo: Final[PriceListRepository] = price_list_repo

    async def handle(self, command: CreatePriceListCommand) -> PriceList:
        existing = await self._price_list_repo.find_by_id(command.id, command.tenant_id)
        if existing:
            raise ConflictError(f"Lista de preços com id {command.id} já existe.")
        price_list = PriceList(
            id=command.id,
            tenant_id=command.tenant_id,
            menu_id=command.menu_id,
            name=command.name,
            description=command.description,
            is_active=command.is_active,
            valid_from=command.valid_from,
            valid_until=command.valid_until,
        )
        await self._price_list_repo.save(price_list)
        return price_list

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"


@dataclass(frozen=True)
class UpdatePriceListCommand:
    price_list_id: int
    tenant_id: str
    name: str
    description: str
    is_active: bool
    valid_from: _dt | None
    valid_until: _dt | None

    def __repr__(self) -> str:
        return f"UpdatePriceListCommand(price_list_id={self.price_list_id}, tenant_id={self.tenant_id!r})"


class UpdatePriceListHandler:
    def __init__(self, price_list_repo: PriceListRepository) -> None:
        self._price_list_repo: Final[PriceListRepository] = price_list_repo

    async def handle(self, command: UpdatePriceListCommand) -> PriceList:
        price_list = await self._price_list_repo.find_by_id(
            command.price_list_id, command.tenant_id
        )
        if not price_list:
            raise NotFoundError("PriceList", command.price_list_id)
        price_list.name = command.name
        price_list.description = command.description
        if command.is_active:
            price_list.activate()
        else:
            price_list.deactivate()
        if command.valid_from:
            price_list.valid_from = command.valid_from
        if command.valid_until:
            price_list.valid_until = command.valid_until
        await self._price_list_repo.save(price_list)
        return price_list

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"


@dataclass(frozen=True)
class DeletePriceListCommand:
    price_list_id: int
    tenant_id: str

    def __repr__(self) -> str:
        return f"DeletePriceListCommand(price_list_id={self.price_list_id}, tenant_id={self.tenant_id!r})"


class DeletePriceListHandler:
    def __init__(self, price_list_repo: PriceListRepository) -> None:
        self._price_list_repo: Final[PriceListRepository] = price_list_repo

    async def handle(self, command: DeletePriceListCommand) -> None:
        price_list = await self._price_list_repo.find_by_id(
            command.price_list_id, command.tenant_id
        )
        if not price_list:
            raise NotFoundError("PriceList", command.price_list_id)
        await self._price_list_repo.delete(command.price_list_id, command.tenant_id)

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"


@dataclass(frozen=True)
class AddPriceListItemCommand:
    price_list_id: int
    tenant_id: str
    item_id: int
    menu_item_id: int
    price: Money

    def __repr__(self) -> str:
        return f"AddPriceListItemCommand(price_list_id={self.price_list_id}, menu_item_id={self.menu_item_id}, price={self.price!r})"


class AddPriceListItemHandler:
    def __init__(self, price_list_repo: PriceListRepository) -> None:
        self._price_list_repo: Final[PriceListRepository] = price_list_repo

    async def handle(self, command: AddPriceListItemCommand) -> PriceListItem:
        price_list = await self._price_list_repo.find_by_id(
            command.price_list_id, command.tenant_id
        )
        if not price_list:
            raise NotFoundError("PriceList", command.price_list_id)

        existing_item = next(
            (i for i in price_list.items if i.menu_item_id == command.menu_item_id), None
        )
        if existing_item:
            price_list.update_item_price(command.menu_item_id, command.price)
        else:
            item = PriceListItem(
                id=command.item_id,
                price_list_id=command.price_list_id,
                menu_item_id=command.menu_item_id,
                price=command.price,
            )
            price_list.add_item(item)

        await self._price_list_repo.save(price_list)
        if existing_item:
            return existing_item
        return price_list.items[-1]

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"


@dataclass(frozen=True)
class RemovePriceListItemCommand:
    price_list_id: int
    tenant_id: str
    menu_item_id: int

    def __repr__(self) -> str:
        return f"RemovePriceListItemCommand(price_list_id={self.price_list_id}, menu_item_id={self.menu_item_id})"


class RemovePriceListItemHandler:
    def __init__(self, price_list_repo: PriceListRepository) -> None:
        self._price_list_repo: Final[PriceListRepository] = price_list_repo

    async def handle(self, command: RemovePriceListItemCommand) -> None:
        price_list = await self._price_list_repo.find_by_id(
            command.price_list_id, command.tenant_id
        )
        if not price_list:
            raise NotFoundError("PriceList", command.price_list_id)
        price_list.remove_item(command.menu_item_id)
        await self._price_list_repo.save(price_list)

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"
