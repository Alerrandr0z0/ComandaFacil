from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.dependencies import db_session
from app.main import app
from app.order.domain.fulfillment import Table
from app.order.domain.order_form import OrderForm
from app.order.domain.order_item import OrderFormItem
from app.order.infrastructure.pg_repository import SQLAlchemyOrderRepository
from app.shared.base_orm import Base
from app.shared.money import Money
from app.shared.value_objects import TableNum

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


@pytest.fixture
async def api_client(sqlite_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Client overriding db_session and mongo_db dependencies to use our temporary SQLite db and a mock MongoDB."""

    async def override_db_session() -> AsyncGenerator[AsyncSession, None]:
        yield sqlite_session

    class MockCollection:
        def __init__(self) -> None:
            self.history: list[dict[str, Any]] = []

        async def replace_one(
            self, filter: dict[str, Any], doc: dict[str, Any], upsert: bool = False
        ) -> None:
            self.history.append(doc)

        async def find_one(
            self, filter: dict[str, Any], projection: dict[str, Any] | None = None
        ) -> dict[str, Any] | None:
            return None

        async def to_list(self, length: int) -> list[dict[str, Any]]:
            return self.history

        def find(
            self, filter: dict[str, Any], projection: dict[str, Any] | None = None
        ) -> MockCollection:
            return self

    mock_collection = MockCollection()

    async def override_mongo_db() -> object:
        class MockDB:
            def __getitem__(self, name: str) -> MockCollection:
                return mock_collection

        return MockDB()

    from app.dependencies import mongo_db

    app.dependency_overrides[db_session] = override_db_session
    app.dependency_overrides[mongo_db] = override_mongo_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-Tenant-ID": "franquia_001"},
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_order_endpoint_success(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
    # Act - Create order with Table Strategy
    response = await api_client.post(
        "/api/v1/order",
        json={"id": 100, "fulfillment_type": "TABLE", "table_number": 3},
    )

    # Assert
    assert response.status_code == 201
    json_data = response.json()
    assert json_data["id"] == 100
    assert json_data["tenant_id"] == "franquia_001"
    assert json_data["state"] == "OPEN"
    assert json_data["fulfillment"]["type"] == "TABLE"
    assert json_data["fulfillment"]["table_number"] == 3
    assert json_data["fulfillment"]["fee"] == "0.00"
    assert json_data["items"] == []

    # Verify relational db persistence
    repo = SQLAlchemyOrderRepository(sqlite_session)
    persisted = await repo.find_by_id(100)
    assert persisted is not None
    assert persisted.tenant_id == "franquia_001"


@pytest.mark.asyncio
async def test_get_order_endpoint_success(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
    # Arrange
    repo = SQLAlchemyOrderRepository(sqlite_session)
    order = OrderForm(id=101, tenant_id="franquia_001")
    order.set_fulfillment_strategy(Table(TableNum(4)))
    await repo.save(order)
    await sqlite_session.commit()

    # Act
    response = await api_client.get("/api/v1/order/101")

    # Assert
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["id"] == 101
    assert json_data["fulfillment"]["table_number"] == 4


@pytest.mark.asyncio
async def test_add_order_item_endpoint_success(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
    # Arrange
    repo = SQLAlchemyOrderRepository(sqlite_session)
    order = OrderForm(id=102, tenant_id="franquia_001")
    order.set_fulfillment_strategy(Table(TableNum(4)))
    await repo.save(order)
    await sqlite_session.commit()

    # Act
    response = await api_client.post(
        "/api/v1/order/102/items",
        json={
            "id": 1,
            "menu_item_id": 200,
            "name_cpy": "X-Burger",
            "price_cpy": "29.90",
            "station_type_cpy": "Grill",
            "quantity": 2,
            "notes": "Extra bacon",
        },
    )

    # Assert
    assert response.status_code == 201
    json_data = response.json()
    assert json_data["id"] == 1
    assert json_data["name_cpy"] == "X-Burger"
    assert json_data["subtotal"] == "59.80"

    # Verify db items
    updated = await repo.find_by_id(102)
    assert updated is not None
    assert len(updated.items) == 1
    assert updated.items[0].name_cpy == "X-Burger"


@pytest.mark.asyncio
async def test_order_full_payment_and_delivery_flow_success(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
    # Arrange - Setup order with item
    repo = SQLAlchemyOrderRepository(sqlite_session)
    order = OrderForm(id=103, tenant_id="franquia_001")
    order.set_fulfillment_strategy(Table(TableNum(5)))
    item = OrderFormItem(
        id=1,
        menu_item_id=200,
        name_cpy="X-Burger",
        price_cpy=Money(Decimal("29.90")),
        station_type_cpy="Grill",
        quantity=1,
    )
    order.add_item(item)
    await repo.save(order)
    await sqlite_session.commit()

    # Act 1: Request Payment
    response1 = await api_client.post("/api/v1/order/103/request-payment")
    assert response1.status_code == 200
    assert response1.json()["payment_requested"] is True

    # Act 2: Process Payment
    response2 = await api_client.post("/api/v1/order/103/process-payment")
    assert response2.status_code == 200
    assert response2.json()["state"] == "PAID"

    # Act 3: Deliver (closes comanda and syncs read model to MongoDB)
    response3 = await api_client.post("/api/v1/order/103/deliver")
    assert response3.status_code == 200
    assert response3.json()["state"] == "CLOSED"

    # Act 4: Verify completed read models history from MongoDB read models
    response4 = await api_client.get("/api/v1/order/history/all")
    assert response4.status_code == 200
    history = response4.json()
    assert len(history) == 1
    assert history[0]["order_id"] == 103
    assert history[0]["fulfillment"]["table"]["table_number"] == 5
    assert history[0]["items"][0]["name"] == "X-Burger"
