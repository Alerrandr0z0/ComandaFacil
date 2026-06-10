from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final, Protocol, runtime_checkable

if TYPE_CHECKING:
    from app.menu.domain.menu import MenuItem, MenuItemRepository
    from app.menu.domain.price_list import PriceList, PriceListRepository


@runtime_checkable
class MenuReadRepository(Protocol):
    async def find_by_id(self, menu_id: int, tenant_id: str, /) -> Any | None: ...
    async def find_all(self, tenant_id: str, /) -> list[Any]: ...


@dataclass(frozen=True)
class GetMenuQuery:
    menu_id: int
    tenant_id: str

    def __repr__(self) -> str:
        return f"GetMenuQuery(menu_id={self.menu_id}, tenant_id={self.tenant_id!r})"


class GetMenuHandler:
    def __init__(self, read_repo: MenuReadRepository) -> None:
        self._read_repo: Final[MenuReadRepository] = read_repo

    async def handle(self, query: GetMenuQuery) -> dict[str, Any] | None:
        return await self._read_repo.find_by_id(query.menu_id, query.tenant_id)

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"


@dataclass(frozen=True)
class ListMenusQuery:
    tenant_id: str

    def __repr__(self) -> str:
        return f"ListMenusQuery(tenant_id={self.tenant_id!r})"


class ListMenusHandler:
    def __init__(self, read_repo: MenuReadRepository) -> None:
        self._read_repo: Final[MenuReadRepository] = read_repo

    async def handle(self, query: ListMenusQuery) -> list[dict[str, Any]]:
        return await self._read_repo.find_all(query.tenant_id)

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"


@dataclass(frozen=True)
class ListMenuItemsQuery:
    tenant_id: str

    def __repr__(self) -> str:
        return f"ListMenuItemsQuery(tenant_id={self.tenant_id!r})"


class ListMenuItemsHandler:
    def __init__(self, item_repo: MenuItemRepository) -> None:
        self._item_repo: Final[MenuItemRepository] = item_repo

    async def handle(self, query: ListMenuItemsQuery) -> list[MenuItem]:
        return await self._item_repo.find_all(query.tenant_id)

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"


@dataclass(frozen=True)
class ListPriceListsQuery:
    tenant_id: str

    def __repr__(self) -> str:
        return f"ListPriceListsQuery(tenant_id={self.tenant_id!r})"


class ListPriceListsHandler:
    def __init__(self, price_list_repo: PriceListRepository) -> None:
        self._repo: Final[PriceListRepository] = price_list_repo

    async def handle(self, query: ListPriceListsQuery) -> list[PriceList]:
        return await self._repo.find_all(query.tenant_id)

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"


@dataclass(frozen=True)
class GetPriceListQuery:
    price_list_id: int
    tenant_id: str

    def __repr__(self) -> str:
        return (
            f"GetPriceListQuery(price_list_id={self.price_list_id}, tenant_id={self.tenant_id!r})"
        )


class GetPriceListHandler:
    def __init__(self, price_list_repo: PriceListRepository) -> None:
        self._repo: Final[PriceListRepository] = price_list_repo

    async def handle(self, query: GetPriceListQuery) -> PriceList | None:
        return await self._repo.find_by_id(query.price_list_id, query.tenant_id)

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"
