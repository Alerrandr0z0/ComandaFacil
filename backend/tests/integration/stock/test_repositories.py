from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.shared.base_orm import Base
from app.shared.value_objects import MeasuredQuantity, MeasurementUnit
from app.stock.domain.enums import MovementType, StockCategory
from app.stock.domain.stock_item import StockItem
from app.stock.domain.stock_movement import StockMovement
from app.stock.infrastructure.pg_repository import (
    SQLAlchemyStockItemRepository,
    SQLAlchemyStockMovementRepository,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


@pytest.fixture
async def sqlite_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session
        await session.rollback()
    await engine.dispose()


@pytest.mark.asyncio
async def test_stock_item_create_and_find(sqlite_session: AsyncSession) -> None:
    # Arrange
    repo = SQLAlchemyStockItemRepository(sqlite_session)
    item = StockItem(
        id=1,
        tenant_id="franquia_001",
        name="Farinha de Trigo",
        category=StockCategory.RAW_MATERIAL.value,
        current_quantity=MeasuredQuantity(50.0, MeasurementUnit.KILOGRAM),
        min_stock_level=10.0,
    )

    # Act
    await repo.save(item)
    await sqlite_session.commit()

    # Assert
    persisted = await repo.find_by_id(1, "franquia_001")
    assert persisted is not None
    assert persisted.id == 1
    assert persisted.name == "Farinha de Trigo"
    assert persisted.category == StockCategory.RAW_MATERIAL.value
    assert persisted.current_quantity.amount == 50.0
    assert persisted.current_quantity.unit == MeasurementUnit.KILOGRAM
    assert persisted.min_stock_level == 10.0
    assert persisted.is_active is True


@pytest.mark.asyncio
async def test_stock_item_find_by_name(sqlite_session: AsyncSession) -> None:
    # Arrange
    repo = SQLAlchemyStockItemRepository(sqlite_session)
    item = StockItem(
        id=2,
        tenant_id="franquia_001",
        name="Açúcar",
        category=StockCategory.RAW_MATERIAL.value,
        current_quantity=MeasuredQuantity(20.0, MeasurementUnit.KILOGRAM),
    )
    await repo.save(item)
    await sqlite_session.commit()

    # Act
    persisted = await repo.find_by_name("Açúcar", "franquia_001")

    # Assert
    assert persisted is not None
    assert persisted.id == 2
    assert persisted.name == "Açúcar"

    # Different tenant should not find
    not_found = await repo.find_by_name("Açúcar", "outra_franquia")
    assert not_found is None


@pytest.mark.asyncio
async def test_stock_item_find_all_tenant_scoped(sqlite_session: AsyncSession) -> None:
    # Arrange
    repo = SQLAlchemyStockItemRepository(sqlite_session)
    item1 = StockItem(
        id=10,
        tenant_id="tenant_a",
        name="Item A",
        category=StockCategory.OTHER.value,
        current_quantity=MeasuredQuantity(10.0, MeasurementUnit.UNIT),
    )
    item2 = StockItem(
        id=20,
        tenant_id="tenant_a",
        name="Item B",
        category=StockCategory.OTHER.value,
        current_quantity=MeasuredQuantity(20.0, MeasurementUnit.UNIT),
    )
    item3 = StockItem(
        id=30,
        tenant_id="tenant_b",
        name="Item C",
        category=StockCategory.OTHER.value,
        current_quantity=MeasuredQuantity(30.0, MeasurementUnit.UNIT),
    )
    await repo.save(item1)
    await repo.save(item2)
    await repo.save(item3)
    await sqlite_session.commit()

    # Act
    all_a = await repo.find_all("tenant_a")

    # Assert
    assert len(all_a) == 2
    assert {i.id for i in all_a} == {10, 20}

    all_b = await repo.find_all("tenant_b")
    assert len(all_b) == 1
    assert all_b[0].id == 30


@pytest.mark.asyncio
async def test_stock_item_find_low_stock(sqlite_session: AsyncSession) -> None:
    # Arrange
    repo = SQLAlchemyStockItemRepository(sqlite_session)
    item_low = StockItem(
        id=50,
        tenant_id="franquia_001",
        name="Tomate",
        category=StockCategory.RAW_MATERIAL.value,
        current_quantity=MeasuredQuantity(3.0, MeasurementUnit.KILOGRAM),
        min_stock_level=10.0,
    )
    item_ok = StockItem(
        id=51,
        tenant_id="franquia_001",
        name="Cebola",
        category=StockCategory.RAW_MATERIAL.value,
        current_quantity=MeasuredQuantity(15.0, MeasurementUnit.KILOGRAM),
        min_stock_level=10.0,
    )
    await repo.save(item_low)
    await repo.save(item_ok)
    await sqlite_session.commit()

    # Act
    low_items = await repo.find_low_stock("franquia_001")

    # Assert
    assert len(low_items) == 1
    assert low_items[0].id == 50
    assert low_items[0].is_low_stock is True


@pytest.mark.asyncio
async def test_stock_item_update(sqlite_session: AsyncSession) -> None:
    # Arrange
    repo = SQLAlchemyStockItemRepository(sqlite_session)
    item = StockItem(
        id=60,
        tenant_id="franquia_001",
        name="Óleo de Soja",
        category=StockCategory.RAW_MATERIAL.value,
        current_quantity=MeasuredQuantity(10.0, MeasurementUnit.LITER),
        min_stock_level=2.0,
        is_active=True,
    )
    await repo.save(item)
    await sqlite_session.commit()

    # Act — modify and save
    item.add_stock(5.0)
    item.min_stock_level = 3.0
    await repo.save(item)
    await sqlite_session.commit()

    # Assert
    persisted = await repo.find_by_id(60, "franquia_001")
    assert persisted is not None
    assert persisted.current_quantity.amount == 15.0
    assert persisted.min_stock_level == 3.0


@pytest.mark.asyncio
async def test_stock_item_delete(sqlite_session: AsyncSession) -> None:
    # Arrange
    repo = SQLAlchemyStockItemRepository(sqlite_session)
    item = StockItem(
        id=70,
        tenant_id="franquia_001",
        name="Descartável",
        category=StockCategory.PACKAGING.value,
        current_quantity=MeasuredQuantity(100.0, MeasurementUnit.UNIT),
    )
    await repo.save(item)
    await sqlite_session.commit()

    # Act
    await repo.delete(70, "franquia_001")

    # Assert
    persisted = await repo.find_by_id(70, "franquia_001")
    assert persisted is None


@pytest.mark.asyncio
async def test_stock_movement_lifecycle(sqlite_session: AsyncSession) -> None:
    # Arrange
    item_repo = SQLAlchemyStockItemRepository(sqlite_session)
    mov_repo = SQLAlchemyStockMovementRepository(sqlite_session)

    item = StockItem(
        id=80,
        tenant_id="franquia_001",
        name="Coca-Cola",
        category=StockCategory.BEVERAGE.value,
        current_quantity=MeasuredQuantity(24.0, MeasurementUnit.UNIT),
    )
    await item_repo.save(item)
    await sqlite_session.commit()

    movement = StockMovement(
        id=0,
        stock_item_id=80,
        movement_type=MovementType.INBOUND,
        quantity_changed=24.0,
        reason="Initial stock",
    )

    # Act
    await mov_repo.save(movement)
    await sqlite_session.commit()

    # Assert
    movements = await mov_repo.find_by_stock_item(80, "franquia_001")
    assert len(movements) == 1
    assert movements[0].stock_item_id == 80
    assert movements[0].movement_type == MovementType.INBOUND
    assert movements[0].quantity_changed == 24.0
    assert movements[0].reason == "Initial stock"
