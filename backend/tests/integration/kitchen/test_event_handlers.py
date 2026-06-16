from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.menu.domain.menu import MenuItem
from app.menu.infrastructure.repositories import SQLAlchemyMenuItemRepository
from app.shared.base_orm import Base
from app.shared.money import Money

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


@pytest.fixture
async def setup_menu_item(sqlite_session: AsyncSession) -> MenuItem:
    repo = SQLAlchemyMenuItemRepository(sqlite_session)
    item = MenuItem(
        id=10,
        tenant_id="franquia_001",
        name="Test Burger",
        description="Juicy burger",
        base_price=Money(Decimal("25.00")),
        station_type="GRILL",
        category_name="Burgers",
        is_available=True,
    )
    await repo.save(item)
    await sqlite_session.commit()
    return item


@pytest.mark.asyncio
async def test_receive_kitchen_order_item_on_order_item_added(
    sqlite_session: AsyncSession,
    setup_menu_item: MenuItem,
) -> None:
    from app.kitchen.application.event_handlers import ReceiveKitchenOrderItemListener
    from app.kitchen.infrastructure.pg_repository import SQLAlchemyKitchenOrderItemRepository
    from app.order.domain.order_events import OrderItemAdded

    # Arrange
    event = OrderItemAdded(
        order_id=200,
        tenant_id="franquia_001",
        item_id=500,
        menu_item_id=10,
        name="Test Burger",
        quantity=1,
        price=Decimal("25.00"),
    )
    listener = ReceiveKitchenOrderItemListener()

    # Act
    await listener(event)

    # Assert
    kds_repo = SQLAlchemyKitchenOrderItemRepository(sqlite_session)
    # The unique ID is item_id * 1000 + sequence_index
    persisted = await kds_repo.find_by_id(500000, "franquia_001")
    assert persisted is not None
    assert persisted.name_cpy == "Test Burger"
    assert persisted.state.name == "WAITING"


@pytest.mark.asyncio
async def test_cancel_kitchen_order_item_on_order_item_cancelled(
    sqlite_session: AsyncSession,
) -> None:
    from app.kitchen.application.event_handlers import CancelKitchenOrderItemListener
    from app.kitchen.domain.kitchen_item import KitchenOrderItem
    from app.kitchen.infrastructure.pg_repository import SQLAlchemyKitchenOrderItemRepository
    from app.order.domain.order_events import OrderItemCancelRequested

    # Arrange: Setup KDS item
    kds_repo = SQLAlchemyKitchenOrderItemRepository(sqlite_session)
    item = KitchenOrderItem(
        id=500000,
        correlation_id=500,
        name_cpy="Test Burger",
        station_type_cpy="GRILL",
        tenant_id="franquia_001",
    )
    await kds_repo.save(item)
    await sqlite_session.commit()

    event = OrderItemCancelRequested(
        order_id=200,
        tenant_id="franquia_001",
        item_id=500,
        name="Test Burger",
        quantity=1,
    )
    listener = CancelKitchenOrderItemListener()

    # Act
    await listener(event)

    # Assert
    persisted = await kds_repo.find_by_id(500000, "franquia_001")
    assert persisted is not None
    assert persisted.state.name == "CANCELLED"


@pytest.mark.asyncio
async def test_cancel_all_kitchen_items_on_order_cancelled(
    sqlite_session: AsyncSession,
) -> None:
    from app.kitchen.application.event_handlers import CancelKitchenOrderItemListener
    from app.kitchen.domain.kitchen_item import KitchenOrderItem
    from app.kitchen.infrastructure.pg_repository import SQLAlchemyKitchenOrderItemRepository
    from app.order.domain.order_events import OrderCancelled
    from app.order.infrastructure.orm_models import OrderFormItemORM

    # Arrange: Setup Order and KDS items
    # We need to simulate the order items in Postgres so the listener can query them
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

    kds_repo = SQLAlchemyKitchenOrderItemRepository(sqlite_session)
    item = KitchenOrderItem(
        id=500000,
        correlation_id=500,
        name_cpy="Test Burger",
        station_type_cpy="GRILL",
        tenant_id="franquia_001",
    )
    await kds_repo.save(item)
    await sqlite_session.commit()

    event = OrderCancelled(
        order_id=200,
        tenant_id="franquia_001",
    )
    listener = CancelKitchenOrderItemListener()

    # Act
    await listener(event)

    # Assert
    persisted = await kds_repo.find_by_id(500000, "franquia_001")
    assert persisted is not None
    assert persisted.state.name == "CANCELLED"
