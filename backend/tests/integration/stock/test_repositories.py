from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.shared.base_orm import Base
from app.shared.value_objects import MeasuredQuantity
from app.stock.domain.enums import StockCategory, TransactionType
from app.stock.domain.recipe import Recipe
from app.stock.domain.stock_item import CompositeStockItem, SimpleStockItem
from app.stock.domain.transaction import StockTransaction
from app.stock.infrastructure.pg_repository import (
    SQLAlchemyRecipeRepository,
    SQLAlchemyStockItemRepository,
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
async def test_simple_stock_item_create_and_find(sqlite_session: AsyncSession) -> None:
    repo = SQLAlchemyStockItemRepository(sqlite_session)
    item = SimpleStockItem(
        id=1,
        tenant_id="franquia_001",
        name="Farinha de Trigo",
        category=StockCategory.RAW_MATERIAL.value,
        unit="kg",
        min_stock_level=10.0,
    )
    # Add initial transaction
    item.add_transaction(
        StockTransaction(0, MeasuredQuantity(Decimal("50"), "kg"), TransactionType.INPUT)
    )

    await repo.save(item)
    await sqlite_session.commit()

    persisted = await repo.find_by_id(1, "franquia_001")
    assert persisted is not None
    assert persisted.id == 1
    assert persisted.name == "Farinha de Trigo"
    assert persisted.get_balance().value == Decimal("50")
    assert persisted.min_stock_level == 10.0


@pytest.mark.asyncio
async def test_composite_stock_item_relations_persistence(sqlite_session: AsyncSession) -> None:
    repo = SQLAlchemyStockItemRepository(sqlite_session)

    # Children
    c1 = SimpleStockItem(id=10, tenant_id="t1", name="Carne", category="RAW_MATERIAL", unit="un")
    c1.add_transaction(
        StockTransaction(0, MeasuredQuantity(Decimal("10"), "un"), TransactionType.INPUT)
    )

    c2 = SimpleStockItem(id=20, tenant_id="t1", name="Pao", category="RAW_MATERIAL", unit="un")
    c2.add_transaction(
        StockTransaction(0, MeasuredQuantity(Decimal("15"), "un"), TransactionType.INPUT)
    )

    # Parent Composite
    comp = CompositeStockItem(
        id=30,
        tenant_id="t1",
        name="Hamburguer",
        category="RAW_MATERIAL",
        unit="un",
    )
    comp.add_component(c1)
    comp.add_component(c2)

    await repo.save(comp)
    await sqlite_session.commit()

    # Load composite
    persisted = await repo.find_by_id(30, "t1")
    assert persisted is not None
    assert isinstance(persisted, CompositeStockItem)
    assert len(persisted.components) == 2
    assert persisted.get_balance().value == Decimal("25")


@pytest.mark.asyncio
async def test_recipe_and_ingredients_persistence(sqlite_session: AsyncSession) -> None:
    item_repo = SQLAlchemyStockItemRepository(sqlite_session)
    recipe_repo = SQLAlchemyRecipeRepository(sqlite_session, item_repo)

    item = SimpleStockItem(
        id=1, tenant_id="t1", name="Chocolate", category="RAW_MATERIAL", unit="g"
    )

    recipe = Recipe(id=10, menu_item_id=200, tenant_id="t1")
    recipe.add_ingredient(item, MeasuredQuantity(Decimal("50"), "g"))

    await recipe_repo.save(recipe)
    await sqlite_session.commit()

    persisted = await recipe_repo.find_by_menu_item(200, "t1")
    assert persisted is not None
    assert persisted.menu_item_id == 200
    ingredients = persisted.get_ingredients()
    assert len(ingredients) == 1
    assert ingredients[0].stock_item.name == "Chocolate"
    assert ingredients[0].quantity.value == Decimal("50")
