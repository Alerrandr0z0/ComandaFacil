from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.dependencies import db_session
from app.main import app
from app.menu.domain.category import Category
from app.menu.domain.menu import Menu, MenuItem
from app.menu.infrastructure.repositories import SQLAlchemyMenuRepository
from app.shared.base_orm import Base

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

    async def override_mongo_db() -> object:
        class MockCollection:
            async def replace_one(self, *args: object, **kwargs: object) -> None:
                pass

            async def delete_one(self, *args: object, **kwargs: object) -> None:
                pass

        class MockDB:
            def __getitem__(self, name: str) -> MockCollection:
                return MockCollection()

        return MockDB()

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
    persisted = await repo.find_by_id(1)
    assert persisted is not None
    assert persisted.name == "Almoço"


@pytest.mark.asyncio
async def test_get_menu_endpoint_success(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
    # Arrange
    repo = SQLAlchemyMenuRepository(sqlite_session)
    menu = Menu(id=1, name="Almoço", description="Pratos executivos")
    item = MenuItem(id=10, name="Feijoada", description="Completa", category=Category("Pratos"))
    menu.add_item(item)
    await repo.save(menu)
    await sqlite_session.commit()

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


@pytest.mark.asyncio
async def test_add_menu_item_endpoint_success(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
    # Arrange
    repo = SQLAlchemyMenuRepository(sqlite_session)
    menu = Menu(id=1, name="Almoço")
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
            "is_available": True,
        },
    )

    # Assert
    assert response.status_code == 201
    json_data = response.json()
    assert json_data["id"] == 10
    assert json_data["name"] == "Suco de Laranja"
    assert json_data["category"] == "Bebidas"

    # Verify db items
    updated = await repo.find_by_id(1)
    assert updated is not None
    assert len(updated.items) == 1
    assert updated.items[0].name == "Suco de Laranja"


@pytest.mark.asyncio
async def test_remove_menu_item_endpoint_success(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
    # Arrange
    repo = SQLAlchemyMenuRepository(sqlite_session)
    menu = Menu(id=1, name="Almoço")
    item = MenuItem(id=10, name="Feijoada", description="Completa", category=Category("Pratos"))
    menu.add_item(item)
    await repo.save(menu)
    await sqlite_session.commit()

    # Act
    response = await api_client.delete("/api/v1/menu/1/items/10")

    # Assert
    assert response.status_code == 200
    assert response.json() == {"detail": "Item removido do cardápio com sucesso."}

    # Verify database
    updated = await repo.find_by_id(1)
    assert updated is not None
    assert len(updated.items) == 0


@pytest.mark.asyncio
async def test_toggle_menu_endpoint_success(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
    # Arrange
    repo = SQLAlchemyMenuRepository(sqlite_session)
    menu = Menu(id=1, name="Almoço", is_active=True)
    await repo.save(menu)
    await sqlite_session.commit()

    # Act - Deactivate Menu
    response = await api_client.patch("/api/v1/menu/1/toggle", json={"activate": False})

    # Assert
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    # Verify db
    updated = await repo.find_by_id(1)
    assert updated is not None
    assert updated.is_active is False
