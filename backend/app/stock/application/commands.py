from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from app.shared.exceptions import ConflictError, NotFoundError
from app.shared.value_objects import MeasuredQuantity, MeasurementUnit
from app.stock.domain.enums import MovementType
from app.stock.domain.stock_item import StockItem, StockItemRepository
from app.stock.domain.stock_movement import StockMovement, StockMovementRepository


@dataclass(frozen=True)
class CreateStockItemCommand:
    id: int
    tenant_id: str
    name: str
    category: str
    current_quantity: float
    unit: str
    min_stock_level: float = 0


class CreateStockItemHandler:
    def __init__(self, repo: StockItemRepository) -> None:
        self._repo: Final[StockItemRepository] = repo

    async def handle(self, command: CreateStockItemCommand) -> StockItem:
        existing = await self._repo.find_by_name(command.name, command.tenant_id)
        if existing:
            raise ConflictError(f"Item de estoque '{command.name}' já existe.")

        item = StockItem(
            id=command.id,
            tenant_id=command.tenant_id,
            name=command.name,
            category=command.category,
            current_quantity=MeasuredQuantity(
                command.current_quantity, MeasurementUnit(command.unit)
            ),
            min_stock_level=command.min_stock_level,
        )
        await self._repo.save(item)
        return item


@dataclass(frozen=True)
class AddStockCommand:
    stock_item_id: int
    tenant_id: str
    quantity: float
    reason: str = ""
    reference_type: str | None = None
    reference_id: int | None = None


class AddStockHandler:
    def __init__(
        self,
        item_repo: StockItemRepository,
        movement_repo: StockMovementRepository,
    ) -> None:
        self._item_repo: Final[StockItemRepository] = item_repo
        self._movement_repo: Final[StockMovementRepository] = movement_repo

    async def handle(self, command: AddStockCommand) -> StockItem:
        item = await self._item_repo.find_by_id(command.stock_item_id, command.tenant_id)
        if not item:
            raise NotFoundError("StockItem", command.stock_item_id)

        item.add_stock(command.quantity)
        await self._item_repo.save(item)

        movement = StockMovement(
            id=0,
            stock_item_id=item.id,
            movement_type=MovementType.INBOUND,
            quantity_changed=command.quantity,
            reason=command.reason,
            reference_type=command.reference_type,
            reference_id=command.reference_id,
        )
        await self._movement_repo.save(movement)

        return item


@dataclass(frozen=True)
class DeductStockCommand:
    stock_item_id: int
    tenant_id: str
    quantity: float
    reason: str = ""
    reference_type: str | None = None
    reference_id: int | None = None


class DeductStockHandler:
    def __init__(
        self,
        item_repo: StockItemRepository,
        movement_repo: StockMovementRepository,
    ) -> None:
        self._item_repo: Final[StockItemRepository] = item_repo
        self._movement_repo: Final[StockMovementRepository] = movement_repo

    async def handle(self, command: DeductStockCommand) -> StockItem:
        item = await self._item_repo.find_by_id(command.stock_item_id, command.tenant_id)
        if not item:
            raise NotFoundError("StockItem", command.stock_item_id)

        item.deduct_stock(command.quantity)
        await self._item_repo.save(item)

        movement = StockMovement(
            id=0,
            stock_item_id=item.id,
            movement_type=MovementType.OUTBOUND,
            quantity_changed=-command.quantity,
            reason=command.reason,
            reference_type=command.reference_type,
            reference_id=command.reference_id,
        )
        await self._movement_repo.save(movement)

        return item


@dataclass(frozen=True)
class AdjustStockCommand:
    stock_item_id: int
    tenant_id: str
    new_quantity: float
    reason: str = ""


class AdjustStockHandler:
    def __init__(
        self,
        item_repo: StockItemRepository,
        movement_repo: StockMovementRepository,
    ) -> None:
        self._item_repo: Final[StockItemRepository] = item_repo
        self._movement_repo: Final[StockMovementRepository] = movement_repo

    async def handle(self, command: AdjustStockCommand) -> StockItem:
        item = await self._item_repo.find_by_id(command.stock_item_id, command.tenant_id)
        if not item:
            raise NotFoundError("StockItem", command.stock_item_id)

        old_amount = item.current_quantity.amount
        item.adjust_stock(command.new_quantity)
        await self._item_repo.save(item)

        movement = StockMovement(
            id=0,
            stock_item_id=item.id,
            movement_type=MovementType.ADJUSTMENT,
            quantity_changed=command.new_quantity - old_amount,
            reason=command.reason,
        )
        await self._movement_repo.save(movement)

        return item


@dataclass(frozen=True)
class SetMinStockLevelCommand:
    stock_item_id: int
    tenant_id: str
    min_stock_level: float


class SetMinStockLevelHandler:
    def __init__(self, repo: StockItemRepository) -> None:
        self._repo: Final[StockItemRepository] = repo

    async def handle(self, command: SetMinStockLevelCommand) -> StockItem:
        item = await self._repo.find_by_id(command.stock_item_id, command.tenant_id)
        if not item:
            raise NotFoundError("StockItem", command.stock_item_id)

        item.set_min_stock_level(command.min_stock_level)
        await self._repo.save(item)
        return item


class StockService:
    """Facade exposing high-level stock operations."""

    def __init__(
        self,
        item_repo: StockItemRepository,
        movement_repo: StockMovementRepository,
    ) -> None:
        self._item_repo: Final[StockItemRepository] = item_repo
        self._movement_repo: Final[StockMovementRepository] = movement_repo

    async def add_stock(
        self,
        stock_item_id: int,
        tenant_id: str,
        quantity: float,
        reason: str = "",
    ) -> StockItem:
        handler = AddStockHandler(self._item_repo, self._movement_repo)
        return await handler.handle(
            AddStockCommand(
                stock_item_id=stock_item_id,
                tenant_id=tenant_id,
                quantity=quantity,
                reason=reason,
            )
        )

    async def deduct_stock(
        self,
        stock_item_id: int,
        tenant_id: str,
        quantity: float,
        reason: str = "",
    ) -> StockItem:
        handler = DeductStockHandler(self._item_repo, self._movement_repo)
        return await handler.handle(
            DeductStockCommand(
                stock_item_id=stock_item_id,
                tenant_id=tenant_id,
                quantity=quantity,
                reason=reason,
            )
        )
