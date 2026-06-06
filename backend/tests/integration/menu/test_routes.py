from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.dependencies import db_session
from app.main import app
from app.menu.domain.menu import Menu, MenuItem
from app.menu.infrastructure.repositories import (
    SQLAlchemyMenuItemRepository,
    SQLAlchemyMenuRepository,
)
from app.shared.base_orm import Base
from app.shared.money import Money
from tests.integration.conftest_helpers import make_mock_db

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

    _store, mock_db = make_mock_db()

    async def override_db_session() -> AsyncGenerator[AsyncSession, None]:
        yield sqlite_session

    async def override_mongo_db() -> object:
        return mock_db

    from app.dependencies import mongo_db

    app.dependency_overrides[db_session] = override_db_session
    app.dependency_overrides[mongo_db] = override_mongo_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-Tenant-ID": "test_franchise"},
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_menu_endpoint_success(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
    # Act - Create Menu
    response = await api_client.post(
        "/api/v1/menu", json={"id": 1, "name": "Almoço", "description": "Pratos executivos"}
    )

    # Assert
    assert response.status_code == 201
    json_data = response.json()
    assert json_data["id"] == 1
    assert json_data["name"] == "Almoço"
    assert json_data["description"] == "Pratos executivos"
    assert json_data["is_active"] is True
    assert json_data["items"] == []

    # Verify db persistence
    repo = SQLAlchemyMenuRepository(sqlite_session)
    persisted = await repo.find_by_id(1, "test_franchise")
    assert persisted is not None
    assert persisted.name == "Almoço"


@pytest.mark.asyncio
async def test_get_menu_endpoint_success(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
    # Arrange — create via API so BackgroundTasks populate Mongo read model
    create_resp = await api_client.post(
        "/api/v1/menu", json={"id": 1, "name": "Almoço", "description": "Pratos executivos"}
    )
    assert create_resp.status_code == 201

    add_resp = await api_client.post(
        "/api/v1/menu/1/items",
        json={
            "id": 10,
            "name": "Feijoada",
            "description": "Completa",
            "category": "Pratos",
            "base_price": 45.00,
            "station_type": "GRILL",
            "is_available": True,
        },
    )
    assert add_resp.status_code == 201

    # Act
    response = await api_client.get("/api/v1/menu/1")

    # Assert
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["id"] == 1
    assert json_data["name"] == "Almoço"
    assert len(json_data["items"]) == 1
    assert json_data["items"][0]["id"] == 10
    assert json_data["items"][0]["name"] == "Feijoada"
    assert json_data["items"][0]["category"] == "Pratos"
    assert float(json_data["items"][0]["price"]) == 45.00


@pytest.mark.asyncio
async def test_add_menu_item_endpoint_success(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
    # Arrange
    repo = SQLAlchemyMenuRepository(sqlite_session)
    menu = Menu(id=1, tenant_id="test_franchise", name="Almoço")
    await repo.save(menu)
    await sqlite_session.commit()

    # Act
    response = await api_client.post(
        "/api/v1/menu/1/items",
        json={
            "id": 10,
            "name": "Suco de Laranja",
            "description": "Copo 300ml",
            "category": "Bebidas",
            "base_price": 8.50,
            "station_type": "BEVERAGE",
            "is_available": True,
        },
    )

    # Assert
    assert response.status_code == 201
    json_data = response.json()
    assert json_data["id"] == 10
    assert json_data["name"] == "Suco de Laranja"
    assert json_data["category"] == "Bebidas"
    assert float(json_data["price"]) == 8.50

    # Verify db items
    updated = await repo.find_by_id(1, "test_franchise")
    assert updated is not None
    assert len(updated.categories) == 1
    assert len(updated.categories[0].items) == 1
    assert updated.categories[0].items[0].menu_item_id == 10


@pytest.mark.asyncio
async def test_remove_menu_item_endpoint_success(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
    # Arrange
    repo = SQLAlchemyMenuRepository(sqlite_session)
    item_repo = SQLAlchemyMenuItemRepository(sqlite_session)

    item = MenuItem(
        id=10,
        tenant_id="test_franchise",
        name="Feijoada",
        description="Completa",
        base_price=Money.from_float(45.00),
        station_type="GRILL",
        category_name="Pratos",
        is_available=True,
    )
    await item_repo.save(item)

    menu = Menu(id=1, tenant_id="test_franchise", name="Almoço")
    menu.add_item_to_category("Pratos", 10)
    await repo.save(menu)
    await sqlite_session.commit()

    # Act
    response = await api_client.delete("/api/v1/menu/1/items/10")

    # Assert
    assert response.status_code == 200
    assert response.json() == {"detail": "Item removido do cardápio com sucesso."}

    # Verify database
    updated = await repo.find_by_id(1, "test_franchise")
    assert updated is not None
    assert len(updated.categories) == 0


@pytest.mark.asyncio
async def test_toggle_menu_endpoint_success(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
    # Arrange
    repo = SQLAlchemyMenuRepository(sqlite_session)
    menu = Menu(id=1, tenant_id="test_franchise", name="Almoço", is_active=True)
    await repo.save(menu)
    await sqlite_session.commit()

    # Act - Deactivate Menu
    response = await api_client.patch("/api/v1/menu/1/toggle", json={"activate": False})

    # Assert
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    # Verify db
    updated = await repo.find_by_id(1, "test_franchise")
    assert updated is not None
    assert updated.is_active is False


@pytest.mark.asyncio
async def test_update_menu_item_price_endpoint_success(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
    # Arrange
    repo = SQLAlchemyMenuRepository(sqlite_session)
    item_repo = SQLAlchemyMenuItemRepository(sqlite_session)

    item = MenuItem(
        id=10,
        tenant_id="test_franchise",
        name="Feijoada",
        description="Completa",
        base_price=Money.from_float(45.00),
        station_type="GRILL",
        category_name="Pratos",
        is_available=True,
    )
    await item_repo.save(item)

    menu = Menu(id=1, tenant_id="test_franchise", name="Almoço")
    menu.add_item_to_category("Pratos", 10)
    await repo.save(menu)
    await sqlite_session.commit()

    # Act - update price
    response = await api_client.patch(
        "/api/v1/menu/1/items/10/price", json={"price": 49.90}
    )

    # Assert
    assert response.status_code == 200
    assert response.json() == {"detail": "Preço do item atualizado com sucesso."}

    # Verify database override
    from app.menu.infrastructure.repositories import SQLAlchemyPriceListRepository
    pl_repo = SQLAlchemyPriceListRepository(sqlite_session)
    updated_menu = await repo.find_by_id(1, "test_franchise")
    assert updated_menu is not None
    assert updated_menu.price_list_id is not None

    price_list = await pl_repo.find_by_id(updated_menu.price_list_id, "test_franchise")
    assert price_list is not None
    assert len(price_list.items) == 1
    assert float(price_list.items[0].price.amount) == 49.90
