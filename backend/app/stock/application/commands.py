from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Final

from app.shared.exceptions import ConflictError, InsufficientStockError, NotFoundError
from app.stock.domain.enums import TransactionType
from app.stock.domain.measured_quantity import MeasuredQuantity
from app.stock.domain.stock_item import SimpleStockItem, StockItem, StockItemRepository
from app.stock.domain.transaction import StockTransaction

if TYPE_CHECKING:
    from app.stock.domain.recipe import RecipeRepository


@dataclass(frozen=True)
class CreateStockItemCommand:
    tenant_id: str
    name: str
    category: str
    current_quantity: Decimal
    unit: str
    initial_cost_amount: Decimal = Decimal("0.0")
    min_stock_level: float = 0.0


class CreateStockItemHandler:
    def __init__(self, repo: StockItemRepository) -> None:
        self._repo: Final[StockItemRepository] = repo

    async def handle(self, command: CreateStockItemCommand) -> StockItem:
        existing = await self._repo.find_by_name(command.name, command.tenant_id)
        if existing:
            raise ConflictError(f"Item de estoque '{command.name}' já existe.")

        item = SimpleStockItem(
            id=0,
            tenant_id=command.tenant_id,
            name=command.name,
            category=command.category,
            unit=command.unit,
            min_stock_level=command.min_stock_level,
        )
        if command.current_quantity > Decimal("0"):
            item.add_transaction(
                StockTransaction(
                    id=0,
                    quantity=MeasuredQuantity(command.current_quantity, command.unit),
                    type=TransactionType.INPUT,
                    cost_amount=command.initial_cost_amount,
                )
            )
        await self._repo.save(item)
        return item


class StockService:
    """Facade exposing high-level stock operations matching the UML diagram."""

    def __init__(
        self,
        item_repo: StockItemRepository,
        recipe_repo: RecipeRepository,
    ) -> None:
        self._item_repo: Final[StockItemRepository] = item_repo
        self._recipe_repo: Final[RecipeRepository] = recipe_repo

    async def add_input(
        self, item_id: int, quantity: Decimal, cost_amount: Decimal, tenant_id: str
    ) -> None:
        item = await self._item_repo.find_by_id(item_id, tenant_id)
        if not item:
            raise NotFoundError("StockItem", item_id)

        # Retrieve unit of simple or composite item
        unit = getattr(item, "unit", "un")
        tx = StockTransaction(
            id=0,
            quantity=MeasuredQuantity(quantity, unit),
            type=TransactionType.INPUT,
            cost_amount=cost_amount,
        )
        item.add_transaction(tx)
        await self._item_repo.save(item)

    async def register_output(
        self,
        item_id: int,
        quantity: Decimal,
        tenant_id: str,
        reason: str = "",
    ) -> None:
        item = await self._item_repo.find_by_id(item_id, tenant_id)
        if not item:
            raise NotFoundError("StockItem", item_id)

        current_balance = item.get_balance()
        if current_balance.value < quantity:
            raise InsufficientStockError(item.name, float(current_balance.value), float(quantity))

        unit = getattr(item, "unit", "un")
        tx = StockTransaction(
            id=0,
            quantity=MeasuredQuantity(quantity, unit),
            type=TransactionType.OUTPUT,
            reason=reason,
        )
        item.add_transaction(tx)
        await self._item_repo.save(item)

    async def adjust(
        self,
        item_id: int,
        quantity: Decimal,
        tenant_id: str,
        reason: str = "",
        transaction_type: TransactionType = TransactionType.ADJUSTMENT,
    ) -> None:
        item = await self._item_repo.find_by_id(item_id, tenant_id)
        if not item:
            raise NotFoundError("StockItem", item_id)

        unit = getattr(item, "unit", "un")
        tx = StockTransaction(
            id=0,
            quantity=MeasuredQuantity(quantity, unit),
            type=transaction_type,
            reason=reason,
        )
        item.add_transaction(tx)
        await self._item_repo.save(item)

    async def register_waste(
        self,
        item_id: int,
        quantity: Decimal,
        tenant_id: str,
        reason: str = "",
    ) -> None:
        item = await self._item_repo.find_by_id(item_id, tenant_id)
        if not item:
            raise NotFoundError("StockItem", item_id)

        current_balance = item.get_balance()
        if current_balance.value < quantity:
            raise InsufficientStockError(item.name, float(current_balance.value), float(quantity))

        unit = getattr(item, "unit", "un")
        tx = StockTransaction(
            id=0,
            quantity=MeasuredQuantity(quantity, unit),
            type=TransactionType.WASTE,
            reason=reason,
        )
        item.add_transaction(tx)
        await self._item_repo.save(item)

    async def deduct_by_recipe(self, menu_item_id: int, tenant_id: str) -> None:
        recipe = await self._recipe_repo.find_by_menu_item(menu_item_id, tenant_id)
        if not recipe:
            return

        for ing in recipe.get_ingredients():
            await self.register_output(
                ing.stock_item.id,
                ing.quantity.value,
                tenant_id,
                reason=f"Recipe deduction for MenuItem {menu_item_id}",
            )

    async def get_balance(self, item_id: int, tenant_id: str) -> MeasuredQuantity:
        item = await self._item_repo.find_by_id(item_id, tenant_id)
        if not item:
            raise NotFoundError("StockItem", item_id)
        return item.get_balance()
