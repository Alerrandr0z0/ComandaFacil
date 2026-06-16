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

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


@pytest.fixture
async def sqlite_session() -> AsyncGenerator[AsyncSession, None]:
    from app.shared import database as _database
    from app.shared.domain_events import EventBus, pending_events_var

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    class TestAsyncSession(AsyncSession):
        async def commit(self) -> None:
            is_wrapped = getattr(self.commit, "__name__", "") == "commit_with_events"
            if is_wrapped:
                await super().commit()
            else:
                events = list(pending_events_var.get() or [])
                pending_events_var.set([])
                await super().commit()
                for event in events:
                    await EventBus.publish(event)

    sf = async_sessionmaker(engine, expire_on_commit=False, class_=TestAsyncSession)

    old_factory = _database.session_factory
    _database.session_factory = sf

    async with sf() as session:
        token = pending_events_var.set([])
        yield session
        await session.rollback()
        pending_events_var.reset(token)

    _database.session_factory = old_factory
    await engine.dispose()


@pytest.fixture
async def api_client(sqlite_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:  # noqa: C901
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

        async def insert_one(self, doc: dict[str, Any], **kwargs: Any) -> None:
            self.history.append(doc)

        async def update_one(
            self, filter: dict[str, Any], update: dict[str, Any], **kwargs: Any
        ) -> None:
            # Simple mock update
            for doc in self.history:
                if doc.get("order_id") == filter.get("order_id") and "$set" in update:
                    doc.update(update["$set"])

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

        def sort(self, *args: Any, **kwargs: Any) -> MockCollection:
            return self

        def limit(self, *args: Any, **kwargs: Any) -> MockCollection:
            return self

    collections: dict[str, MockCollection] = {}

    async def override_mongo_db() -> object:
        class MockDB:
            def __getitem__(self, name: str) -> MockCollection:
                if name not in collections:
                    collections[name] = MockCollection()
                return collections[name]

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
    persisted = await repo.find_by_id(100, "franquia_001")
    assert persisted is not None
    assert persisted.tenant_id == "franquia_001"


@pytest.mark.asyncio
async def test_get_order_endpoint_success(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
    # Arrange
    repo = SQLAlchemyOrderRepository(sqlite_session)
    order = OrderForm(id=101, tenant_id="franquia_001")
    order.set_fulfillment_strategy(Table(4))
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
    order.set_fulfillment_strategy(Table(4))
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
    updated = await repo.find_by_id(102, "franquia_001")
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
    order.set_fulfillment_strategy(Table(5))
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


@pytest.mark.asyncio
async def test_get_order_timeline_success(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
    import datetime
    import hashlib

    from app.auth.infrastructure.orm_models import AuditLogORM

    # 1. Seed some fake audit logs for order 105
    # Safe tenant hash mapping for franquia_001
    t_id = int(hashlib.sha256(b"franquia_001").hexdigest(), 16) % 1000000

    log1 = AuditLogORM(
        tenant_id=t_id,
        actor_id=502,
        actor_name="Marcos Garçom",
        action="ORDER_CREATED",
        entity_type="order",
        entity_id="105",
        details="Comanda ID 105 criada com tipo de atendimento TABLE.",
        created_at=datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=5),
    )
    sqlite_session.add(log1)
    await sqlite_session.commit()

    # 2. Call the timeline endpoint
    response = await api_client.get("/api/v1/order/105/timeline")
    assert response.status_code == 200
    timeline = response.json()
    assert len(timeline) == 1
    assert timeline[0]["actor_name"] == "Marcos Garçom"
    assert timeline[0]["action"] == "ORDER_CREATED"
    assert timeline[0]["details"] == "Comanda ID 105 criada com tipo de atendimento TABLE."


@pytest.mark.asyncio
async def test_cancel_item_when_active_order_then_sets_item_canceled_and_updates_total(
    api_client: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    from app.menu.domain.menu import MenuItem
    from app.menu.infrastructure.repositories import SQLAlchemyMenuItemRepository
    from app.shared.money import Money

    menu_repo = SQLAlchemyMenuItemRepository(sqlite_session)
    await menu_repo.save(
        MenuItem(
            id=10,
            tenant_id="franquia_001",
            name="Pizza",
            description="Pizza",
            base_price=Money(Decimal("39.90")),
            station_type="Grill",
            category_name="Pizza",
            is_available=True,
        )
    )
    await menu_repo.save(
        MenuItem(
            id=11,
            tenant_id="franquia_001",
            name="Suco",
            description="Suco",
            base_price=Money(Decimal("8.50")),
            station_type="Beverage",
            category_name="Suco",
            is_available=True,
        )
    )
    await sqlite_session.commit()

    # Arrange - criar comanda com 2 itens
    create_resp = await api_client.post(
        "/api/v1/order",
        json={
            "fulfillment_type": "TABLE",
            "display_code": "MESA-10",
            "table_number": 10,
        },
        headers={"X-Tenant-ID": "franquia_001"},
    )
    assert create_resp.status_code == 201
    order = create_resp.json()
    order_id = order["id"]

    # Adicionar item 1: Pizza 39.90 x2 = 79.80
    item1_resp = await api_client.post(
        f"/api/v1/order/{order_id}/items",
        json={
            "id": 1001,
            "menu_item_id": 10,
            "name_cpy": "Pizza",
            "price_cpy": "39.90",
            "station_type_cpy": "Grill",
            "quantity": 2,
        },
        headers={"X-Tenant-ID": "franquia_001"},
    )
    assert item1_resp.status_code == 201

    # Adicionar item 2: Suco 8.50 x1 = 8.50
    item2_resp = await api_client.post(
        f"/api/v1/order/{order_id}/items",
        json={
            "id": 1002,
            "menu_item_id": 11,
            "name_cpy": "Suco",
            "price_cpy": "8.50",
            "station_type_cpy": "Beverage",
            "quantity": 1,
        },
        headers={"X-Tenant-ID": "franquia_001"},
    )
    assert item2_resp.status_code == 201

    # Act - cancelar o Suco (item 1002)
    cancel_resp = await api_client.patch(
        f"/api/v1/order/{order_id}/items/1002/cancel",
        headers={"X-Tenant-ID": "franquia_001"},
    )

    # Assert
    assert cancel_resp.status_code == 200
    updated_order = cancel_resp.json()

    # Total deve ser apenas Pizza (79.80), Suco cancelado
    assert Decimal(updated_order["total"]) == Decimal("79.80")

    # Item 1002 deve estar CANCELED
    suco = next(i for i in updated_order["items"] if i["id"] == 1002)
    assert suco["status"] == "CANCELED"

    # Item 1001 deve permanecer WAITING
    pizza = next(i for i in updated_order["items"] if i["id"] == 1001)
    assert pizza["status"] == "WAITING"


@pytest.mark.asyncio
async def test_cancel_item_when_order_paid_then_raises_bad_request(
    api_client: AsyncClient,
) -> None:
    # Arrange - criar comanda paga
    create_resp = await api_client.post(
        "/api/v1/order",
        json={
            "fulfillment_type": "TABLE",
            "display_code": "MESA-11",
            "table_number": 11,
        },
        headers={"X-Tenant-ID": "franquia_001"},
    )
    assert create_resp.status_code == 201
    order_id = create_resp.json()["id"]

    # Adicionar item
    item_resp = await api_client.post(
        f"/api/v1/order/{order_id}/items",
        json={
            "id": 2001,
            "menu_item_id": 10,
            "name_cpy": "Pizza",
            "price_cpy": "39.90",
            "station_type_cpy": "Grill",
            "quantity": 1,
        },
        headers={"X-Tenant-ID": "franquia_001"},
    )
    assert item_resp.status_code == 201

    # Request payment then pay the order
    req_resp = await api_client.post(
        f"/api/v1/order/{order_id}/request-payment",
        headers={"X-Tenant-ID": "franquia_001"},
    )
    assert req_resp.status_code == 200

    pay_resp = await api_client.post(
        f"/api/v1/order/{order_id}/process-payment",
        headers={"X-Tenant-ID": "franquia_001"},
    )
    assert pay_resp.status_code == 200

    # Act
    cancel_resp = await api_client.patch(
        f"/api/v1/order/{order_id}/items/2001/cancel",
        headers={"X-Tenant-ID": "franquia_001"},
    )

    # Assert
    assert cancel_resp.status_code == 400
