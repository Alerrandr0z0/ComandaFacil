from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from app.kitchen.infrastructure.mongo_read_repository import (
        MongoKitchenReadRepository,
    )


@dataclass(frozen=True)
class GetActiveKitchenItemsQuery:
    tenant_id: str
    station_type: str

    def __repr__(self) -> str:
        return (
            f"GetActiveKitchenItemsQuery(tenant={self.tenant_id!r}, station={self.station_type!r})"
        )


class GetActiveKitchenItemsHandler:
    def __init__(self, read_repo: MongoKitchenReadRepository) -> None:
        self._read_repo: Final[MongoKitchenReadRepository] = read_repo

    async def handle(
        self, query: GetActiveKitchenItemsQuery
    ) -> list[dict[str, Any]]:
        """Fetches all active kitchen items for a station from the Mongo read model."""
        return await self._read_repo.find_active_by_station(
            query.station_type, query.tenant_id
        )
