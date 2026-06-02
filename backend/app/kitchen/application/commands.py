from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from app.kitchen.domain.kitchen_item import KitchenOrder_Item
from app.kitchen.infrastructure.websocket_manager import kds_ws_manager
from app.shared.exceptions import NotFoundError

if TYPE_CHECKING:
    from app.kitchen.domain.repository import KitchenOrderItemRepository


@dataclass(frozen=True)
class ReceiveKitchenItemCommand:
    correlation_id: int
    name_cpy: str
    station_type_cpy: str
    tenant_id: str

    def __repr__(self) -> str:
        return (
            f"ReceiveKitchenItemCommand(correlation_id={self.correlation_id}, "
            f"name={self.name_cpy!r}, station={self.station_type_cpy!r}, tenant={self.tenant_id!r})"
        )


class ReceiveKitchenItemHandler:
    def __init__(self, item_repo: KitchenOrderItemRepository) -> None:
        self._item_repo: Final[KitchenOrderItemRepository] = item_repo

    async def handle(self, command: ReceiveKitchenItemCommand) -> KitchenOrder_Item:
        existing = await self._item_repo.find_by_correlation(command.correlation_id)
        if existing:
            return existing

        # We can map correlation_id directly as the primary ID (since it's a 1-to-1 aggregate snapshot)
        item = KitchenOrder_Item(
            id=command.correlation_id,
            correlation_id=command.correlation_id,
            name_cpy=command.name_cpy,
            station_type_cpy=command.station_type_cpy,
            tenant_id=command.tenant_id,
        )
        await self._item_repo.save(item)

        # Notify KDS clients connected to this specific station
        await kds_ws_manager.broadcast_to_station(
            tenant_id=command.tenant_id,
            station_type=command.station_type_cpy,
            event_data={
                "event": "ITEM_RECEIVED",
                "item": {
                    "id": item.id,
                    "correlation_id": item.correlation_id,
                    "name_cpy": item.name_cpy,
                    "station_type_cpy": item.station_type_cpy,
                    "state": item.state.name,
                },
            },
        )
        return item


@dataclass(frozen=True)
class PrepareKitchenItemCommand:
    item_id: int

    def __repr__(self) -> str:
        return f"PrepareKitchenItemCommand(item_id={self.item_id})"


class PrepareKitchenItemHandler:
    def __init__(self, item_repo: KitchenOrderItemRepository) -> None:
        self._item_repo: Final[KitchenOrderItemRepository] = item_repo

    async def handle(self, command: PrepareKitchenItemCommand) -> KitchenOrder_Item:
        item = await self._item_repo.find_by_id(command.item_id)
        if not item:
            raise NotFoundError("Kitchen Item", command.item_id)

        item.prepare()
        await self._item_repo.save(item)

        # Broadcast update to connected station screens
        await kds_ws_manager.broadcast_to_station(
            tenant_id=item.tenant_id,
            station_type=item.station_type_cpy,
            event_data={
                "event": "ITEM_PREPARING",
                "item": {
                    "id": item.id,
                    "correlation_id": item.correlation_id,
                    "name_cpy": item.name_cpy,
                    "station_type_cpy": item.station_type_cpy,
                    "state": item.state.name,
                },
            },
        )
        return item


@dataclass(frozen=True)
class MarkKitchenItemReadyCommand:
    item_id: int

    def __repr__(self) -> str:
        return f"MarkKitchenItemReadyCommand(item_id={self.item_id})"


class MarkKitchenItemReadyHandler:
    def __init__(self, item_repo: KitchenOrderItemRepository) -> None:
        self._item_repo: Final[KitchenOrderItemRepository] = item_repo

    async def handle(self, command: MarkKitchenItemReadyCommand) -> KitchenOrder_Item:
        item = await self._item_repo.find_by_id(command.item_id)
        if not item:
            raise NotFoundError("Kitchen Item", command.item_id)

        item.mark_as_ready()
        await self._item_repo.save(item)

        # Broadcast ready state to alert KDS displays
        await kds_ws_manager.broadcast_to_station(
            tenant_id=item.tenant_id,
            station_type=item.station_type_cpy,
            event_data={
                "event": "ITEM_READY",
                "item": {
                    "id": item.id,
                    "correlation_id": item.correlation_id,
                    "name_cpy": item.name_cpy,
                    "station_type_cpy": item.station_type_cpy,
                    "state": item.state.name,
                },
            },
        )
        return item


@dataclass(frozen=True)
class CancelKitchenItemCommand:
    item_id: int

    def __repr__(self) -> str:
        return f"CancelKitchenItemCommand(item_id={self.item_id})"


class CancelKitchenItemHandler:
    def __init__(self, item_repo: KitchenOrderItemRepository) -> None:
        self._item_repo: Final[KitchenOrderItemRepository] = item_repo

    async def handle(self, command: CancelKitchenItemCommand) -> KitchenOrder_Item:
        item = await self._item_repo.find_by_id(command.item_id)
        if not item:
            raise NotFoundError("Kitchen Item", command.item_id)

        item.cancel()
        await self._item_repo.save(item)

        # Broadcast cancellation to connected KDS displays
        await kds_ws_manager.broadcast_to_station(
            tenant_id=item.tenant_id,
            station_type=item.station_type_cpy,
            event_data={
                "event": "ITEM_CANCELLED",
                "item": {
                    "id": item.id,
                    "correlation_id": item.correlation_id,
                    "name_cpy": item.name_cpy,
                    "station_type_cpy": item.station_type_cpy,
                    "state": item.state.name,
                },
            },
        )
        return item


class KitchenService:
    """Facade service corresponding to the Javadoc/UML KitchenService definition."""

    def __init__(self, item_repo: KitchenOrderItemRepository) -> None:
        self._item_repo: Final[KitchenOrderItemRepository] = item_repo
        self._receive_handler = ReceiveKitchenItemHandler(item_repo)
        self._prepare_handler = PrepareKitchenItemHandler(item_repo)
        self._ready_handler = MarkKitchenItemReadyHandler(item_repo)
        self._cancel_handler = CancelKitchenItemHandler(item_repo)

    async def receive_item(
        self, correlation_id: int, name_cpy: str, station_type_cpy: str, tenant_id: str
    ) -> KitchenOrder_Item:
        cmd = ReceiveKitchenItemCommand(
            correlation_id=correlation_id,
            name_cpy=name_cpy,
            station_type_cpy=station_type_cpy,
            tenant_id=tenant_id,
        )
        return await self._receive_handler.handle(cmd)

    async def prepare_item(self, item_id: int) -> KitchenOrder_Item:
        cmd = PrepareKitchenItemCommand(item_id=item_id)
        return await self._prepare_handler.handle(cmd)

    async def mark_item_ready(self, item_id: int) -> KitchenOrder_Item:
        cmd = MarkKitchenItemReadyCommand(item_id=item_id)
        return await self._ready_handler.handle(cmd)

    async def cancel_item(self, item_id: int) -> KitchenOrder_Item:
        cmd = CancelKitchenItemCommand(item_id=item_id)
        return await self._cancel_handler.handle(cmd)

    async def cancelITem(self, kitchenItemId: int, session: int) -> KitchenOrder_Item:  # noqa: N802, N803, ARG002
        """Alternative signature matching Javadoc CamelCase exactly."""
        return await self.cancel_item(kitchenItemId)
