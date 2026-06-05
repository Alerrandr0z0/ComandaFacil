from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.order.domain.enums import FulfillmentStatus
from app.order.domain.fulfillment import Delivery, Table
from app.order.domain.order_form import OrderForm
from app.order.domain.order_item import OrderFormItem
from app.order.infrastructure.mongo_repository import OrderHistoryMongoRepository
from app.order.infrastructure.pg_repository import SQLAlchemyOrderRepository
from app.shared.base_orm import Base
from app.shared.money import Money
from app.shared.value_objects import Address, TableNum

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Async session fixture utilizing in-memory SQLite for extremely fast integration tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    # Create all tables in the SQLite database
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session
        await session.rollback()

    await engine.dispose()


@pytest.mark.asyncio
async def test_order_repository_lifecycle_with_table(db_session: AsyncSession) -> None:
    # Arrange
    repo = SQLAlchemyOrderRepository(db_session)
    order = OrderForm(id=42, tenant_id="franquia_001")
    order.set_fulfillment_strategy(Table(TableNum(5)))

    item = OrderFormItem(
        id=1,
        menu_item_id=10,
        name_cpy="Pizza",
        price_cpy=Money(Decimal("39.90")),
        station_type_cpy="Grill",
        quantity=2,
        notes="Sem cebola",
    )
    order.add_item(item)

    # 1. Save new order
    await repo.save(order)
    await db_session.commit()

    # 2. Retrieve order and verify mappings
    retrieved = await repo.find_by_id(42, "franquia_001")
    assert retrieved is not None
    assert retrieved.id == 42
    assert retrieved.tenant_id == "franquia_001"
    assert retrieved.state.name == "OPEN"
    assert len(retrieved.items) == 1
    assert retrieved.items[0].id == 1
    assert retrieved.items[0].name_cpy == "Pizza"
    assert retrieved.items[0].price_cpy == Money(Decimal("39.90"))
    assert retrieved.items[0].notes == "Sem cebola"

    # Verify strategy mappings
    strat = retrieved.fulfillment_strategy
    assert isinstance(strat, Table)
    assert strat.table_num.value == 5
    assert strat.get_status() == FulfillmentStatus.READY_FOR_PICKUP

    # 3. Update order state and strategy
    retrieved.request_payment()
    retrieved.process_payment()
    retrieved.deliver()
    await repo.save(retrieved)
    await db_session.commit()

    # 4. Verify updates
    updated = await repo.find_by_id(42, "franquia_001")
    assert updated is not None
    assert updated.state.name == "CLOSED"
    assert updated.fulfillment_strategy is not None
    assert updated.fulfillment_strategy.get_status() == FulfillmentStatus.DELIVERED

    # 5. Delete order and verify cascade deletion of items
    await repo.delete(42, "franquia_001")
    await db_session.commit()

    deleted = await repo.find_by_id(42, "franquia_001")
    assert deleted is None


@pytest.mark.asyncio
async def test_order_repository_lifecycle_with_delivery(db_session: AsyncSession) -> None:
    # Arrange
    repo = SQLAlchemyOrderRepository(db_session)
    order = OrderForm(id=43, tenant_id="franquia_001")

    addr = Address("Rua A", "100", "Bairro X", "São Paulo", "SP", "01001-000")
    delivery = Delivery(address=addr, estimated_time=45, tracking_code=98765)
    order.set_fulfillment_strategy(delivery)

    # 1. Save order in open state
    await repo.save(order)
    await db_session.commit()

    # 2. Retrieve and check delivery details
    retrieved = await repo.find_by_id(43, "franquia_001")
    assert retrieved is not None
    assert retrieved.fulfillment_strategy is not None
    strat = retrieved.fulfillment_strategy
    assert isinstance(strat, Delivery)
    assert strat.address.street == "Rua A"
    assert strat.address.postal_code == "01001-000"
    assert strat.estimated_time == 45
    assert strat.tracking_code == 98765
    assert strat.state.name == "AWAITING_PICKUP"
    assert strat.get_status() == FulfillmentStatus.READY_FOR_PICKUP

    # 3. Dispatch delivery and fail it (physical tracking)
    strat.dispatch()
    strat.fail()
    await repo.save(retrieved)
    await db_session.commit()

    # Verify failed transit status in DB
    updated = await repo.find_by_id(43, "franquia_001")
    assert updated is not None
    assert updated.fulfillment_strategy is not None
    assert updated.fulfillment_strategy.get_status() == FulfillmentStatus.RETURNED
    assert updated.fulfillment_strategy.state.name == "FAILED_DELIVERY"  # type: ignore


@pytest.mark.asyncio
async def test_mongo_order_history_repository() -> None:
    # Arrange
    class MockCollection:
        def __init__(self) -> None:
            self.data: dict[int, dict[str, Any]] = {}

        async def replace_one(
            self, filter: dict[str, Any], doc: dict[str, Any], upsert: bool = False
        ) -> None:
            self.data[filter["order_id"]] = doc

        async def find_one(
            self, filter: dict[str, Any], projection: dict[str, Any] | None = None
        ) -> dict[str, Any] | None:
            doc = self.data.get(filter["order_id"])
            if doc and doc.get("tenant_id") != filter.get("tenant_id"):
                return None
            if doc and projection and "_id" in projection:
                return {k: v for k, v in doc.items() if k != "_id"}
            return doc

        async def to_list(self, length: int) -> list[dict[str, Any]]:
            return list(self.data.values())

        def find(
            self, filter: dict[str, Any], projection: dict[str, Any] | None = None
        ) -> MockCollection:
            return self

    class MockDB:
        def __init__(self) -> None:
            self.coll = MockCollection()

        def __getitem__(self, name: str) -> MockCollection:
            return self.coll

    mock_db = MockDB()
    mongo_repo = OrderHistoryMongoRepository(mock_db)

    order = OrderForm(id=100, tenant_id="franquia_002")
    addr = Address("Rua B", "200", "Bairro Y", "Rio", "RJ", "20002-000")
    order.set_fulfillment_strategy(Delivery(address=addr))
    item = OrderFormItem(
        id=1,
        menu_item_id=20,
        name_cpy="Soda",
        price_cpy=Money(Decimal("6.00")),
        station_type_cpy="Beverage",
        quantity=3,
    )
    order.add_item(item)

    # Act - Save to Mongo read model
    await mongo_repo.save(order)

    # Assert - Retrieve from Mongo read model
    doc = await mongo_repo.find_by_id(100, "franquia_002")
    assert doc is not None
    assert doc["order_id"] == 100
    assert doc["tenant_id"] == "franquia_002"
    assert doc["total"] == "25.00"  # 18.00 items + 7.00 delivery fee
    assert doc["fulfillment"]["type"] == "DELIVERY"
    assert doc["fulfillment"]["delivery"]["delivery_state"] == "AWAITING_PICKUP"
    assert len(doc["items"]) == 1
    assert doc["items"][0]["name"] == "Soda"
    assert doc["items"][0]["subtotal"] == "18.00"
