from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from app.kitchen.domain.kitchen_item import KitchenOrder_Item
    from app.kitchen.domain.repository import KitchenOrderItemRepository


@dataclass(frozen=True)
class GetActiveKitchenItemsQuery:
    tenant_id: str
    station_type: str

    def __repr__(self) -> str:
        return (
            f"GetActiveKitchenItemsQuery(tenant={self.tenant_id!r}, station={self.station_type!r})"
        )


class GetActiveKitchenItemsHandler:
    def __init__(self, item_repo: KitchenOrderItemRepository) -> None:
        self._item_repo: Final[KitchenOrderItemRepository] = item_repo

    async def handle(self, query: GetActiveKitchenItemsQuery) -> list[KitchenOrder_Item]:
        """Fetches all items destined for a station that are currently active (in WAITING or PREPARING state)."""
        items = await self._item_repo.find_by_station(query.station_type, query.tenant_id)
        # Filter out terminal states (READY, CANCELLED)
        return [item for item in items if item.state.name in ("WAITING", "PREPARING")]
