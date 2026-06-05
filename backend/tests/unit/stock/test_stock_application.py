from __future__ import annotations

from decimal import Decimal

import pytest

from app.shared.exceptions import ConflictError
from app.shared.value_objects import MeasuredQuantity
from app.stock.application.commands import (
    CreateStockItemCommand,
    CreateStockItemHandler,
    StockService,
)
from app.stock.domain.enums import TransactionType
from app.stock.domain.recipe import Recipe
from app.stock.domain.stock_item import SimpleStockItem, StockItem


class InMemoryStockItemRepository:
    def __init__(self) -> None:
        self._items: dict[int, StockItem] = {}

    async def find_by_id(self, id: int, tenant_id: str) -> StockItem | None:
        item = self._items.get(id)
        return item if item and item.tenant_id == tenant_id else None

    async def find_by_name(self, name: str, tenant_id: str) -> StockItem | None:
        for item in self._items.values():
            if item.name == name and item.tenant_id == tenant_id:
                return item
        return None

    async def find_all(self, tenant_id: str) -> list[StockItem]:
        return [i for i in self._items.values() if i.tenant_id == tenant_id]

    async def find_low_stock(self, tenant_id: str) -> list[StockItem]:
        return [i for i in self._items.values() if i.tenant_id == tenant_id and i.is_low_stock]

    async def save(self, item: StockItem) -> None:
        self._items[item.id] = item

    async def delete(self, id: int, tenant_id: str) -> None:
        self._items.pop(id, None)

    def add_item(self, item: StockItem) -> None:
        self._items[item.id] = item


class InMemoryRecipeRepository:
    def __init__(self) -> None:
        self._recipes: dict[int, Recipe] = {}

    async def find_by_menu_item(self, menu_item_id: int, tenant_id: str) -> Recipe | None:
        for r in self._recipes.values():
            if r.menu_item_id == menu_item_id and r.tenant_id == tenant_id:
                return r
        return None

    async def save(self, recipe: Recipe) -> None:
        self._recipes[recipe.id] = recipe


@pytest.fixture
def item_repo() -> InMemoryStockItemRepository:
    return InMemoryStockItemRepository()


@pytest.fixture
def recipe_repo() -> InMemoryRecipeRepository:
    return InMemoryRecipeRepository()


@pytest.fixture
def existing_item(item_repo: InMemoryStockItemRepository) -> StockItem:
    item = SimpleStockItem(
        id=1,
        tenant_id="franquia_001",
        name="Farinha",
        category="RAW_MATERIAL",
        unit="kg",
        min_stock_level=2.0,
    )
    item_repo.add_item(item)
    return item


@pytest.mark.unit
async def test_create_stock_item_when_new_then_creates_successfully(
    item_repo: InMemoryStockItemRepository,
) -> None:
    handler = CreateStockItemHandler(item_repo)
    command = CreateStockItemCommand(
        id=1,
        tenant_id="franquia_001",
        name="Coca-Cola",
        category="BEVERAGE",
        current_quantity=Decimal("50"),
        unit="un",
    )

    item = await handler.handle(command)

    assert item.name == "Coca-Cola"
    assert item.get_balance().value == Decimal("50")
    assert item.get_balance().unit == "un"


@pytest.mark.unit
async def test_create_stock_item_when_duplicate_name_then_raises(
    item_repo: InMemoryStockItemRepository,
    existing_item: StockItem,
) -> None:
    handler = CreateStockItemHandler(item_repo)
    command = CreateStockItemCommand(
        id=2,
        tenant_id="franquia_001",
        name="Farinha",
        category="RAW_MATERIAL",
        current_quantity=Decimal("5"),
        unit="kg",
    )

    with pytest.raises(ConflictError, match="já existe"):
        await handler.handle(command)


@pytest.mark.unit
async def test_stock_service_add_input(
    item_repo: InMemoryStockItemRepository,
    recipe_repo: InMemoryRecipeRepository,
    existing_item: StockItem,
) -> None:
    service = StockService(item_repo, recipe_repo)
    await service.add_input(1, Decimal("10"), "franquia_001")

    assert existing_item.get_balance().value == Decimal("10")
    assert len(existing_item.transactions) == 1
    assert existing_item.transactions[0].type == TransactionType.INPUT


@pytest.mark.unit
async def test_stock_service_register_output(
    item_repo: InMemoryStockItemRepository,
    recipe_repo: InMemoryRecipeRepository,
    existing_item: StockItem,
) -> None:
    service = StockService(item_repo, recipe_repo)
    # Add initial stock
    await service.add_input(1, Decimal("10"), "franquia_001")

    # Deduct stock
    await service.register_output(1, Decimal("4"), "franquia_001", "Venda")

    assert existing_item.get_balance().value == Decimal("6")


@pytest.mark.unit
async def test_stock_service_adjust(
    item_repo: InMemoryStockItemRepository,
    recipe_repo: InMemoryRecipeRepository,
    existing_item: StockItem,
) -> None:
    service = StockService(item_repo, recipe_repo)
    await service.add_input(1, Decimal("10"), "franquia_001")

    await service.adjust(1, Decimal("15"), "Ajuste físico", "franquia_001")

    assert existing_item.get_balance().value == Decimal("15")


@pytest.mark.unit
async def test_stock_service_register_waste(
    item_repo: InMemoryStockItemRepository,
    recipe_repo: InMemoryRecipeRepository,
    existing_item: StockItem,
) -> None:
    service = StockService(item_repo, recipe_repo)
    await service.add_input(1, Decimal("10"), "franquia_001")

    await service.register_waste(1, Decimal("2"), "franquia_001")

    assert existing_item.get_balance().value == Decimal("8")


@pytest.mark.unit
async def test_stock_service_deduct_by_recipe(
    item_repo: InMemoryStockItemRepository,
    recipe_repo: InMemoryRecipeRepository,
    existing_item: StockItem,
) -> None:
    service = StockService(item_repo, recipe_repo)
    await service.add_input(1, Decimal("10"), "franquia_001")

    # Create recipe
    recipe = Recipe(id=1, menu_item_id=101, tenant_id="franquia_001")
    recipe.add_ingredient(existing_item, MeasuredQuantity(Decimal("0.5"), "kg"))
    await recipe_repo.save(recipe)

    # Deduct recipe
    await service.deduct_by_recipe(101, "franquia_001")

    assert existing_item.get_balance().value == Decimal("9.5")
