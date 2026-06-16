from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.order.infrastructure.orm_models import OrderFormItemORM
from app.shared.base_orm import Base
from app.stock.infrastructure.orm_models import (
    RecipeIngredientORM,
    RecipeORM,
    StockItemORM,
    StockTransactionORM,
)
from app.stock.infrastructure.pg_repository import SQLAlchemyStockItemRepository

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


@pytest.fixture
async def sqlite_session() -> AsyncGenerator[AsyncSession, None]:
    """In-memory SQLite session with all database schemas generated."""
    from app.shared import database as _database

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    sf = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    # Monkeypatch global database session factory to point to our test SQLite database
    old_factory = _database.session_factory
    _database.session_factory = sf

    async with sf() as session:
        yield session
        await session.rollback()

    # Restore the original factory after tests complete
    _database.session_factory = old_factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_stock_deduction_on_kitchen_item_status_changed_ready(
    sqlite_session: AsyncSession,
) -> None:
    from app.kitchen.domain.kitchen_events import KitchenItemStatusChanged
    from app.stock.application.event_handlers import StockDeductionListener

    # 1. Arrange: setup order item in PG
    sqlite_session.add(
        OrderFormItemORM(
            id=500,
            order_id=200,
            menu_item_id=10,
            name_cpy="Test Burger",
            price_cpy=Decimal("25.00"),
            station_type_cpy="GRILL",
            quantity=1,
            status="WAITING",
        )
    )

    # 2. Setup stock item with 10.0 kg
    stock_item = StockItemORM(
        id=105,
        tenant_id="franquia_001",
        name="Stock Item A",
        category="RAW_MATERIAL",
        type="SIMPLE",
        unit="kg",
        min_stock_level=1.0,
        is_active=True,
    )
    sqlite_session.add(stock_item)
    tx = StockTransactionORM(
        id=1005,
        stock_item_id=105,
        transaction_type="INPUT",
        quantity_value=Decimal("10.0"),
        quantity_unit="kg",
        cost_amount=Decimal("15.0"),
    )
    sqlite_session.add(tx)

    # 3. Setup recipe: menu item 10 needs 2.0 kg of Stock Item A
    recipe = RecipeORM(id=205, menu_item_id=10, tenant_id="franquia_001")
    sqlite_session.add(recipe)
    ing = RecipeIngredientORM(
        id=305,
        recipe_id=205,
        stock_item_id=105,
        quantity_value=Decimal("2.0"),
        quantity_unit="kg",
    )
    sqlite_session.add(ing)

    await sqlite_session.commit()

    # Act: Dispatch status change event
    event = KitchenItemStatusChanged(
        item_id=500000,
        tenant_id="franquia_001",
        correlation_id=500,
        name="Test Burger",
        old_state="PREPARING",
        new_state="READY",
    )
    listener = StockDeductionListener()
    await listener(event)

    # Assert: Stock balance should be 8.0 kg (10.0 - 2.0)
    sqlite_session.expire_all()
    item_repo = SQLAlchemyStockItemRepository(sqlite_session)
    loaded_item = await item_repo.find_by_id(105, "franquia_001")
    assert loaded_item is not None
    assert loaded_item.get_balance().value == Decimal("8.0")
