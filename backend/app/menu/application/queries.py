from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from app.menu.infrastructure.mongo_read_repository import (
        MongoMenuReadRepository,
    )


@dataclass(frozen=True)
class GetMenuQuery:
    menu_id: int
    tenant_id: str

    def __repr__(self) -> str:
        return f"GetMenuQuery(menu_id={self.menu_id}, tenant_id={self.tenant_id!r})"


class GetMenuHandler:
    def __init__(self, read_repo: MongoMenuReadRepository) -> None:
        self._read_repo: Final[MongoMenuReadRepository] = read_repo

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
    def __init__(self, read_repo: MongoMenuReadRepository) -> None:
        self._read_repo: Final[MongoMenuReadRepository] = read_repo

    async def handle(self, query: ListMenusQuery) -> list[dict[str, Any]]:
        return await self._read_repo.find_all(query.tenant_id)

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"
