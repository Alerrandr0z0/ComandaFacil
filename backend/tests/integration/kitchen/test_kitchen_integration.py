from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.dependencies import db_session
from app.kitchen.domain.kitchen_item import KitchenOrderItem
from app.kitchen.domain.kitchen_station import Beverage, Grill
from app.kitchen.infrastructure.pg_repository import (
    SQLAlchemyKitchenOrderItemRepository,
    SQLAlchemyKitchenStationRepository,
)
from app.main import app
from app.order.domain.fulfillment import Table
from app.order.domain.order_form import OrderForm
from app.order.infrastructure.pg_repository import SQLAlchemyOrderRepository
from app.shared.base_orm import Base
from tests.integration.conftest_helpers import make_mock_db

_KITCHEN_MOCK: list[object] = []

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


@pytest.fixture
async def sqlite_session() -> AsyncGenerator[AsyncSession, None]:
    """In-memory SQLite session with all database schemas generated."""
    import app.shared.database

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    # Monkeypatch global database session factory to point to our test SQLite database
    old_factory = app.shared.database.session_factory
    app.shared.database.session_factory = session_factory

    async with session_factory() as session:
        yield session
        await session.rollback()

    # Restore the original factory after tests complete
    app.shared.database.session_factory = old_factory
    await engine.dispose()


@pytest.fixture
async def api_client(sqlite_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTP Client that overrides db_session to use our temporary SQLite db."""

    async def override_db_session() -> AsyncGenerator[AsyncSession, None]:
        yield sqlite_session

    _store, mock_db = make_mock_db()
    _KITCHEN_MOCK.clear()
    _KITCHEN_MOCK.append(mock_db)

    async def override_mongo_db() -> object:
        return mock_db

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
async def test_kitchen_station_persistence_and_query_success(sqlite_session: AsyncSession) -> None:
    # Arrange
    repo = SQLAlchemyKitchenStationRepository(sqlite_session)
    grill = Grill(id=1, tenant_id="franquia_001", is_active=True)
    bev = Beverage(id=2, tenant_id="franquia_001", is_active=False)

    # Act
    await repo.save(grill)
    await repo.save(bev)
    await sqlite_session.commit()

    # Assert
    grills = await repo.find_by_type("franquia_001", "GRILL")
    bevs = await repo.find_by_type("franquia_001", "BEVERAGE")

    assert len(grills) == 1
    assert grills[0].station_type == "GRILL"
    assert grills[0].is_active is True

    assert len(bevs) == 1
    assert bevs[0].station_type == "BEVERAGE"
    assert bevs[0].is_active is False


@pytest.mark.asyncio
async def test_kitchen_order_item_persistence_success(sqlite_session: AsyncSession) -> None:
    # Arrange
    repo = SQLAlchemyKitchenOrderItemRepository(sqlite_session)
    item = KitchenOrderItem(
        id=42,
        correlation_id=42,
        name_cpy="Classic Burger",
        station_type_cpy="GRILL",
        tenant_id="franquia_001",
    )

    # Act
    await repo.save(item)
    await sqlite_session.commit()

    # Assert
    persisted = await repo.find_by_id(42, "franquia_001")
    assert persisted is not None
    assert persisted.correlation_id == 42
    assert persisted.name_cpy == "Classic Burger"
    assert persisted.station_type_cpy == "GRILL"
    assert persisted.state.name == "WAITING"

    persisted_by_corr = await repo.find_by_correlation(42, "franquia_001")
    assert persisted_by_corr is not None
    assert persisted_by_corr.id == 42


@pytest.mark.asyncio
async def test_kds_http_lifecycle_endpoints_success(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
    # Arrange
    repo = SQLAlchemyKitchenOrderItemRepository(sqlite_session)
    item = KitchenOrderItem(
        id=99,
        correlation_id=99,
        name_cpy="Orange Juice",
        station_type_cpy="BEVERAGE",
        tenant_id="franquia_001",
    )
    await repo.save(item)
    await sqlite_session.commit()

    # Sync to Mongo read model (since the test writes directly to Postgres)
    from app.kitchen.infrastructure.kitchen_read_sync import KitchenReadModelSync

    await KitchenReadModelSync(_KITCHEN_MOCK[0]).sync(item)

    # Act & Assert 1: Get Active Items
    get_res = await api_client.get("/api/v1/kitchen/items?station_type=BEVERAGE")
    assert get_res.status_code == 200
    items = get_res.json()
    assert len(items) == 1
    assert items[0]["name_cpy"] == "Orange Juice"
    assert items[0]["state"] == "WAITING"

    # Act & Assert 2: Transition to PREPARING
    prep_res = await api_client.patch("/api/v1/kitchen/items/99/prepare")
    assert prep_res.status_code == 200
    assert prep_res.json()["state"] == "PREPARING"

    # Act & Assert 3: Transition to READY
    ready_res = await api_client.patch("/api/v1/kitchen/items/99/ready")
    assert ready_res.status_code == 200
    assert ready_res.json()["state"] == "READY"

    # Act & Assert 4: Verify recently completed terminal states are still returned (for front-end KDS display)
    get_res_ready = await api_client.get("/api/v1/kitchen/items?station_type=BEVERAGE")
    items_after = get_res_ready.json()
    assert len(items_after) == 1
    assert items_after[0]["state"] == "READY"


@pytest.mark.asyncio
async def test_kds_websocket_and_background_task_dispatch_flow_success(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
    # Arrange: Setup OrderForm
    order_repo = SQLAlchemyOrderRepository(sqlite_session)
    order = OrderForm(id=200, tenant_id="franquia_001")
    order.set_fulfillment_strategy(Table(12))
    await order_repo.save(order)
    await sqlite_session.commit()

    # Connect to WebSocket (KDS Display Screen subscribing for BEVERAGE channel)
    # Using client's WebSocket capabilities
    from fastapi.testclient import TestClient

    # TestClient supports synchronous/async WebSockets perfectly
    client = TestClient(app)

    from app.dependencies import mongo_db

    # Override session dependency on the TestClient app instance too
    async def override_db_session() -> AsyncGenerator[AsyncSession, None]:
        yield sqlite_session

    _store2, mock_db2 = make_mock_db()

    async def override_mongo_db() -> object:
        return mock_db2

    app.dependency_overrides[db_session] = override_db_session
    app.dependency_overrides[mongo_db] = override_mongo_db

    with client.websocket_connect(
        "/api/v1/kitchen/ws?station_type=BEVERAGE&tenant_id=franquia_001"
    ) as ws:
        # Act: Add a beverage item to the OrderForm. This triggers background task dispatch.
        response = client.post(
            "/api/v1/order/200/items",
            json={
                "id": 500,
                "menu_item_id": 10,
                "name_cpy": "Milkshake",
                "price_cpy": "18.50",
                "station_type_cpy": "BEVERAGE",
                "quantity": 1,
                "notes": "",
            },
            headers={"X-Tenant-ID": "franquia_001"},
        )
        assert response.status_code == 201

        # Give small timeframe for BackgroundTask execution to complete
        await asyncio.sleep(0.2)

        # Assert: The WebSocket client should receive real-time KDS frame notify
        event_data = ws.receive_json()
        assert event_data["event"] == "ITEM_RECEIVED"
        assert event_data["item"]["correlation_id"] == 500
        assert event_data["item"]["name_cpy"] == "Milkshake"
        assert event_data["item"]["state"] == "WAITING"

        # Act 2: Prepare the item via API
        prep_res = client.patch(
            "/api/v1/kitchen/items/500/prepare",
            headers={"X-Tenant-ID": "franquia_001"},
        )
        assert prep_res.status_code == 200

        # Assert 2: WebSocket should receive preparing event
        event_prep = ws.receive_json()
        assert event_prep["event"] == "ITEM_PREPARING"
        assert event_prep["item"]["id"] == 500
        assert event_prep["item"]["state"] == "PREPARING"

    app.dependency_overrides.clear()
