from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from app.menu.domain.menu import Menu, MenuRepository


@dataclass(frozen=True)
class GetMenuQuery:
    menu_id: int

    def __repr__(self) -> str:
        return f"GetMenuQuery(menu_id={self.menu_id})"


class GetMenuHandler:
    def __init__(self, menu_repo: MenuRepository) -> None:
        self._menu_repo: Final[MenuRepository] = menu_repo

    async def handle(self, query: GetMenuQuery) -> Menu | None:
        return await self._menu_repo.find_by_id(query.menu_id)

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"


@dataclass(frozen=True)
class ListMenusQuery:
    def __repr__(self) -> str:
        return "ListMenusQuery()"


class ListMenusHandler:
    def __init__(self, menu_repo: MenuRepository) -> None:
        self._menu_repo: Final[MenuRepository] = menu_repo

    async def handle(self, _query: ListMenusQuery) -> list[Menu]:
        return await self._menu_repo.find_all()

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"
