from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from app.menu.domain.category import Category
from app.menu.domain.menu import Menu, MenuItem, MenuRepository
from app.shared.exceptions import ConflictError, NotFoundError


@dataclass(frozen=True)
class CreateMenuCommand:
    id: int
    name: str
    description: str = ""

    def __repr__(self) -> str:
        return f"CreateMenuCommand(id={self.id}, name={self.name!r})"


class CreateMenuHandler:
    def __init__(self, menu_repo: MenuRepository) -> None:
        self._menu_repo: Final[MenuRepository] = menu_repo

    async def handle(self, command: CreateMenuCommand) -> Menu:
        existing = await self._menu_repo.find_by_id(command.id)
        if existing:
            raise ConflictError(f"Cardápio com id {command.id} já existe.")

        menu = Menu(
            id=command.id,
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
    item_id: int
    name: str
    description: str
    category: str
    image_url: str | None = None
    is_available: bool = True

    def __repr__(self) -> str:
        return f"AddMenuItemCommand(menu_id={self.menu_id}, item_id={self.item_id}, name={self.name!r})"


class AddMenuItemHandler:
    def __init__(self, menu_repo: MenuRepository) -> None:
        self._menu_repo: Final[MenuRepository] = menu_repo

    async def handle(self, command: AddMenuItemCommand) -> MenuItem:
        menu = await self._menu_repo.find_by_id(command.menu_id)
        if not menu:
            raise NotFoundError("Cardápio", command.menu_id)

        item = MenuItem(
            id=command.item_id,
            name=command.name,
            description=command.description,
            category=Category(command.category),
            image_url=command.image_url,
            is_available=command.is_available,
        )
        menu.add_item(item)
        await self._menu_repo.save(menu)
        return item

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"


@dataclass(frozen=True)
class RemoveMenuItemCommand:
    menu_id: int
    item_id: int

    def __repr__(self) -> str:
        return f"RemoveMenuItemCommand(menu_id={self.menu_id}, item_id={self.item_id})"


class RemoveMenuItemHandler:
    def __init__(self, menu_repo: MenuRepository) -> None:
        self._menu_repo: Final[MenuRepository] = menu_repo

    async def handle(self, command: RemoveMenuItemCommand) -> None:
        menu = await self._menu_repo.find_by_id(command.menu_id)
        if not menu:
            raise NotFoundError("Cardápio", command.menu_id)
        menu.remove_item(command.item_id)
        await self._menu_repo.save(menu)

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"


@dataclass(frozen=True)
class ToggleMenuCommand:
    menu_id: int
    activate: bool

    def __repr__(self) -> str:
        return f"ToggleMenuCommand(menu_id={self.menu_id}, activate={self.activate})"


class ToggleMenuHandler:
    def __init__(self, menu_repo: MenuRepository) -> None:
        self._menu_repo: Final[MenuRepository] = menu_repo

    async def handle(self, command: ToggleMenuCommand) -> Menu:
        menu = await self._menu_repo.find_by_id(command.menu_id)
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

    def __repr__(self) -> str:
        return f"DeleteMenuCommand(menu_id={self.menu_id})"


class DeleteMenuHandler:
    def __init__(self, menu_repo: MenuRepository) -> None:
        self._menu_repo: Final[MenuRepository] = menu_repo

    async def handle(self, command: DeleteMenuCommand) -> None:
        menu = await self._menu_repo.find_by_id(command.menu_id)
        if not menu:
            raise NotFoundError("Cardápio", command.menu_id)
        await self._menu_repo.delete(command.menu_id)

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"
