from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from app.shared.exceptions import ConflictError, InsufficientStockError, NotFoundError
from app.shared.value_objects import MeasuredQuantity, MeasurementUnit
from app.stock.domain.enums import MovementType
from app.stock.domain.stock_item import StockItem

if TYPE_CHECKING:
    from app.stock.domain.stock_movement import StockMovement


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


class InMemoryStockMovementRepository:
    def __init__(self) -> None:
        self._movements: list[StockMovement] = []
        self._next_id: int = 1

    async def find_by_stock_item(self, stock_item_id: int, tenant_id: str) -> list[StockMovement]:
        return [m for m in self._movements if m.stock_item_id == stock_item_id]

    async def save(self, movement: StockMovement) -> None:
        object.__setattr__(movement, "id", self._next_id)
        self._next_id += 1
        self._movements.append(movement)


@pytest.fixture
def item_repo() -> InMemoryStockItemRepository:
    return InMemoryStockItemRepository()


@pytest.fixture
def movement_repo() -> InMemoryStockMovementRepository:
    return InMemoryStockMovementRepository()


@pytest.fixture
def existing_item(item_repo: InMemoryStockItemRepository) -> StockItem:
    item = StockItem(
        id=1,
        tenant_id="franquia_001",
        name="Farinha",
        category="RAW_MATERIAL",
        current_quantity=MeasuredQuantity(10.0, MeasurementUnit.KILOGRAM),
        min_stock_level=2.0,
    )
    item_repo.add_item(item)
    return item


# ─── CreateStockItem ──────────────────────────────────────────────────────


@pytest.mark.unit
async def test_create_stock_item_when_new_then_creates_successfully(
    item_repo: InMemoryStockItemRepository,
) -> None:
    # Arrange
    from app.stock.application.commands import (
        CreateStockItemCommand,
        CreateStockItemHandler,
    )

    handler = CreateStockItemHandler(item_repo)
    command = CreateStockItemCommand(
        id=1,
        tenant_id="franquia_001",
        name="Coca-Cola",
        category="BEVERAGE",
        current_quantity=50.0,
        unit="un",
    )

    # Act
    item = await handler.handle(command)

    # Assert
    assert item.name == "Coca-Cola"
    assert item.current_quantity.amount == 50.0
    assert item.current_quantity.unit == MeasurementUnit.UNIT


@pytest.mark.unit
async def test_create_stock_item_when_duplicate_name_then_raises(
    item_repo: InMemoryStockItemRepository,
    existing_item: StockItem,
) -> None:
    # Arrange
    from app.stock.application.commands import (
        CreateStockItemCommand,
        CreateStockItemHandler,
    )

    handler = CreateStockItemHandler(item_repo)
    command = CreateStockItemCommand(
        id=2,
        tenant_id="franquia_001",
        name="Farinha",
        category="RAW_MATERIAL",
        current_quantity=5.0,
        unit="kg",
    )

    # Act & Assert
    with pytest.raises(ConflictError, match="já existe"):
        await handler.handle(command)


# ─── AddStock ─────────────────────────────────────────────────────────────


@pytest.mark.unit
async def test_add_stock_when_item_exists_then_increases_and_records(
    item_repo: InMemoryStockItemRepository,
    movement_repo: InMemoryStockMovementRepository,
    existing_item: StockItem,
) -> None:
    # Arrange
    from app.stock.application.commands import AddStockCommand, AddStockHandler

    handler = AddStockHandler(item_repo, movement_repo)
    command = AddStockCommand(
        stock_item_id=1, tenant_id="franquia_001", quantity=5.0, reason="Reabastecimento"
    )

    # Act
    item = await handler.handle(command)

    # Assert
    assert item.current_quantity.amount == 15.0
    movements = await movement_repo.find_by_stock_item(1, "franquia_001")
    assert len(movements) == 1
    assert movements[0].movement_type == MovementType.INBOUND
    assert movements[0].quantity_changed == 5.0


@pytest.mark.unit
async def test_add_stock_when_item_not_found_then_raises(
    item_repo: InMemoryStockItemRepository,
    movement_repo: InMemoryStockMovementRepository,
) -> None:
    # Arrange
    from app.stock.application.commands import AddStockCommand, AddStockHandler

    handler = AddStockHandler(item_repo, movement_repo)

    # Act & Assert
    with pytest.raises(NotFoundError):
        await handler.handle(
            AddStockCommand(stock_item_id=999, tenant_id="franquia_001", quantity=5.0)
        )


# ─── DeductStock ──────────────────────────────────────────────────────────


@pytest.mark.unit
async def test_deduct_stock_when_sufficient_then_decreases_and_records(
    item_repo: InMemoryStockItemRepository,
    movement_repo: InMemoryStockMovementRepository,
    existing_item: StockItem,
) -> None:
    # Arrange
    from app.stock.application.commands import DeductStockCommand, DeductStockHandler

    handler = DeductStockHandler(item_repo, movement_repo)
    command = DeductStockCommand(
        stock_item_id=1, tenant_id="franquia_001", quantity=3.0, reason="Venda"
    )

    # Act
    item = await handler.handle(command)

    # Assert
    assert item.current_quantity.amount == 7.0
    movements = await movement_repo.find_by_stock_item(1, "franquia_001")
    assert len(movements) == 1
    assert movements[0].movement_type == MovementType.OUTBOUND
    assert movements[0].quantity_changed == -3.0


@pytest.mark.unit
async def test_deduct_stock_when_insufficient_then_raises(
    item_repo: InMemoryStockItemRepository,
    movement_repo: InMemoryStockMovementRepository,
    existing_item: StockItem,
) -> None:
    # Arrange
    from app.stock.application.commands import DeductStockCommand, DeductStockHandler

    handler = DeductStockHandler(item_repo, movement_repo)

    # Act & Assert
    with pytest.raises(InsufficientStockError):
        await handler.handle(
            DeductStockCommand(stock_item_id=1, tenant_id="franquia_001", quantity=100.0)
        )


# ─── AdjustStock ──────────────────────────────────────────────────────────


@pytest.mark.unit
async def test_adjust_stock_when_valid_then_sets_and_records(
    item_repo: InMemoryStockItemRepository,
    movement_repo: InMemoryStockMovementRepository,
    existing_item: StockItem,
) -> None:
    # Arrange
    from app.stock.application.commands import AdjustStockCommand, AdjustStockHandler

    handler = AdjustStockHandler(item_repo, movement_repo)
    command = AdjustStockCommand(
        stock_item_id=1, tenant_id="franquia_001", new_quantity=8.0, reason="Contagem física"
    )

    # Act
    item = await handler.handle(command)

    # Assert
    assert item.current_quantity.amount == 8.0
    movements = await movement_repo.find_by_stock_item(1, "franquia_001")
    assert len(movements) == 1
    assert movements[0].movement_type == MovementType.ADJUSTMENT
    assert movements[0].quantity_changed == -2.0  # 8 - 10 = -2


# ─── SetMinStockLevel ──────────────────────────────────────────────────────


@pytest.mark.unit
async def test_set_min_stock_level_when_item_exists_then_updates(
    item_repo: InMemoryStockItemRepository,
    existing_item: StockItem,
) -> None:
    # Arrange
    from app.stock.application.commands import (
        SetMinStockLevelCommand,
        SetMinStockLevelHandler,
    )

    handler = SetMinStockLevelHandler(item_repo)

    # Act
    item = await handler.handle(
        SetMinStockLevelCommand(stock_item_id=1, tenant_id="franquia_001", min_stock_level=5.0)
    )

    # Assert
    assert item.min_stock_level == 5.0


# ─── Queries ──────────────────────────────────────────────────────────────


@pytest.mark.unit
async def test_get_stock_item_when_exists_then_returns(
    item_repo: InMemoryStockItemRepository,
    existing_item: StockItem,
) -> None:
    # Arrange
    from app.stock.application.queries import GetStockItemHandler, GetStockItemQuery

    handler = GetStockItemHandler(item_repo)

    # Act
    item = await handler.handle(GetStockItemQuery(stock_item_id=1, tenant_id="franquia_001"))

    # Assert
    assert item.id == 1  # type: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess]
    assert item.name == "Farinha"  # type: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess]


@pytest.mark.unit
async def test_get_stock_item_when_not_found_then_returns_none(
    item_repo: InMemoryStockItemRepository,
) -> None:
    # Arrange
    from app.stock.application.queries import GetStockItemHandler, GetStockItemQuery

    handler = GetStockItemHandler(item_repo)

    # Act
    result = await handler.handle(GetStockItemQuery(stock_item_id=999, tenant_id="franquia_001"))

    # Assert
    assert result is None


@pytest.mark.unit
async def test_list_stock_items_when_multiple_then_returns_all(
    item_repo: InMemoryStockItemRepository,
) -> None:
    # Arrange
    items = [
        StockItem(
            1, "t1", "Arroz", "RAW_MATERIAL", MeasuredQuantity(10.0, MeasurementUnit.KILOGRAM)
        ),
        StockItem(
            2, "t1", "Feijão", "RAW_MATERIAL", MeasuredQuantity(5.0, MeasurementUnit.KILOGRAM)
        ),
        StockItem(3, "t1", "Coca", "BEVERAGE", MeasuredQuantity(20.0, MeasurementUnit.UNIT)),
    ]
    for item in items:
        item_repo.add_item(item)

    from app.stock.application.queries import (
        ListStockItemsHandler,
        ListStockItemsQuery,
    )

    handler = ListStockItemsHandler(item_repo)

    # Act
    items = await handler.handle(ListStockItemsQuery(tenant_id="t1"))

    # Assert
    assert len(items) == 3


@pytest.mark.unit
async def test_list_stock_items_when_low_stock_filter_then_returns_only_low(
    item_repo: InMemoryStockItemRepository,
) -> None:
    # Arrange
    items = [
        StockItem(
            1,
            "t1",
            "Arroz",
            "RAW_MATERIAL",
            MeasuredQuantity(10.0, MeasurementUnit.KILOGRAM),
            min_stock_level=15.0,
        ),  # LOW
        StockItem(
            2,
            "t1",
            "Feijão",
            "RAW_MATERIAL",
            MeasuredQuantity(20.0, MeasurementUnit.KILOGRAM),
            min_stock_level=5.0,
        ),  # OK
    ]
    for item in items:
        item_repo.add_item(item)

    from app.stock.application.queries import (
        ListStockItemsHandler,
        ListStockItemsQuery,
    )

    handler = ListStockItemsHandler(item_repo)

    # Act
    items = await handler.handle(ListStockItemsQuery(tenant_id="t1", low_stock_only=True))

    # Assert
    assert len(items) == 1
    assert items[0].name == "Arroz"  # type: ignore[reportAttributeAccessIssue]


# ─── StockService ──────────────────────────────────────────────────────────


@pytest.mark.unit
async def test_stock_service_add_and_deduct(
    item_repo: InMemoryStockItemRepository,
    movement_repo: InMemoryStockMovementRepository,
) -> None:
    # Arrange
    from app.stock.application.commands import StockService

    service = StockService(item_repo, movement_repo)
    item = StockItem(
        1,
        "t1",
        "Teste",
        "OTHER",
        MeasuredQuantity(10.0, MeasurementUnit.UNIT),
    )
    item_repo.add_item(item)

    # Act
    await service.add_stock(1, "t1", 5.0, "Compra")
    await service.deduct_stock(1, "t1", 3.0, "Venda")

    # Assert
    item = await item_repo.find_by_id(1, "t1")
    assert item is not None
    assert item.current_quantity.amount == 12.0
