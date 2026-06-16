from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.order.application.commands import CancelOrderItemCommand, CancelOrderItemHandler
from app.order.domain.fulfillment import Table
from app.order.domain.order_form import OrderForm
from app.order.domain.order_item import OrderFormItem
from app.order.infrastructure.pg_repository import SQLAlchemyOrderRepository
from app.shared.base_orm import Base
from app.shared.command_bus import CommandBus
from app.shared.middlewares import UnitOfWorkMiddleware
from app.shared.money import Money

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
    await engine.dispose()


@pytest.mark.asyncio
async def test_command_bus_cancel_item_when_active_order_then_item_canceled(
    sqlite_session: AsyncSession,
) -> None:
    # Arrange
    repo = SQLAlchemyOrderRepository(sqlite_session)
    order = OrderForm(id=100, tenant_id="franquia_001", display_code="MESA-10")
    order.set_fulfillment_strategy(Table(10))

    pizza = OrderFormItem(
        id=1001,
        menu_item_id=10,
        name_cpy="Pizza",
        price_cpy=Money(Decimal("39.90")),
        station_type_cpy="Grill",
        quantity=2,
    )
    suco = OrderFormItem(
        id=1002,
        menu_item_id=11,
        name_cpy="Suco",
        price_cpy=Money(Decimal("8.50")),
        station_type_cpy="Beverage",
        quantity=1,
    )
    order.add_item(pizza)
    order.add_item(suco)
    await repo.save(order)
    await sqlite_session.commit()

    handler = CancelOrderItemHandler(SQLAlchemyOrderRepository(sqlite_session))
    bus = CommandBus(
        handlers={CancelOrderItemCommand: handler},
        middlewares=[UnitOfWorkMiddleware(sqlite_session)],
    )

    # Act
    result = await bus.dispatch(
        CancelOrderItemCommand(order_id=100, item_id=1002, tenant_id="franquia_001")
    )

    # Assert
    canceled_item = next(i for i in result.items if i.id == 1002)
    assert canceled_item.status.value == "CANCELED"
    assert canceled_item.canceled_quantity == 1
    assert canceled_item.quantity == 1  # original preserved

    remaining_item = next(i for i in result.items if i.id == 1001)
    assert remaining_item.status.value == "WAITING"
    assert remaining_item.quantity == 2

    # Verify persistence via repository
    persisted = await repo.find_by_id(100, "franquia_001")
    assert persisted is not None
    assert Decimal(str(persisted.total().amount)) == Decimal("79.80")


@pytest.mark.asyncio
async def test_command_bus_cancel_item_when_handler_fails_then_rolls_back(
    sqlite_session: AsyncSession,
) -> None:
    # Arrange
    repo = SQLAlchemyOrderRepository(sqlite_session)
    order = OrderForm(id=200, tenant_id="franquia_001", display_code="MESA-20")
    order.set_fulfillment_strategy(Table(20))

    item = OrderFormItem(
        id=2001,
        menu_item_id=10,
        name_cpy="Pizza",
        price_cpy=Money(Decimal("39.90")),
        station_type_cpy="Grill",
        quantity=1,
    )
    order.add_item(item)
    await repo.save(order)
    await sqlite_session.commit()

    handler = CancelOrderItemHandler(SQLAlchemyOrderRepository(sqlite_session))
    bus = CommandBus(
        handlers={CancelOrderItemCommand: handler},
        middlewares=[UnitOfWorkMiddleware(sqlite_session)],
    )

    # Act & Assert — cancel item that doesn't exist in order
    with pytest.raises(Exception, match="não encontrado"):
        await bus.dispatch(
            CancelOrderItemCommand(order_id=200, item_id=9999, tenant_id="franquia_001")
        )

    # Verify rollback: item still WAITING in DB
    persisted = await repo.find_by_id(200, "franquia_001")
    assert persisted is not None
    non_canceled = next(i for i in persisted.items if i.id == 2001)
    assert non_canceled.status.value == "WAITING"
