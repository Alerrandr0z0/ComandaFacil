from __future__ import annotations

import pytest
from decimal import Decimal
from typing import TYPE_CHECKING

from app.order.domain.order_form import OrderForm
from app.order.domain.order_item import OrderFormItem
from app.order.domain.enums import OrderItemStatus
from app.order.infrastructure.pg_repository import SQLAlchemyOrderRepository
from app.shared.money import Money

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.shared.base_orm import Base
from collections.abc import AsyncGenerator

if TYPE_CHECKING:
    pass


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
async def test_order_item_status_sync_on_kitchen_item_status_changed(
    sqlite_session: AsyncSession,
) -> None:
    from app.order.application.event_handlers import OrderFormItemStatusListener
    from app.kitchen.domain.kitchen_events import KitchenItemStatusChanged

    # Arrange: Setup Order and Item in Postgres
    order_repo = SQLAlchemyOrderRepository(sqlite_session)
    order = OrderForm(id=200, tenant_id="franquia_001")
    item = OrderFormItem(
        id=500,
        menu_item_id=10,
        name_cpy="Test Burger",
        price_cpy=Money(Decimal("25.00")),
        station_type_cpy="GRILL",
        quantity=1,
        status=OrderItemStatus.WAITING,
    )
    order.add_item(item)
    # Clear events
    order.collect_events()
    await order_repo.save(order)
    await sqlite_session.commit()

    event = KitchenItemStatusChanged(
        item_id=500000,
        tenant_id="franquia_001",
        correlation_id=500,
        name="Test Burger",
        old_state="WAITING",
        new_state="READY",
    )
    listener = OrderFormItemStatusListener()

    # Act
    await listener(event)

    # Assert
    sqlite_session.expire_all()
    persisted = await order_repo.find_by_id(200, "franquia_001")
    assert persisted is not None
    assert persisted.items[0].status == OrderItemStatus.READY
