from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.dependencies import db_session
from app.main import app
from app.shared.base_orm import Base
from app.shared.value_objects import MeasuredQuantity, MeasurementUnit
from app.stock.domain.enums import StockCategory
from app.stock.domain.stock_item import StockItem
from app.stock.infrastructure.pg_repository import SQLAlchemyStockItemRepository
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
        headers={"X-Tenant-ID": "franquia_001"},
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_stock_item_endpoint_success(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
    # Act
    response = await api_client.post(
        "/api/v1/stock/items",
        json={
            "id": 1,
            "name": "Farinha de Trigo",
            "category": "RAW_MATERIAL",
            "current_quantity": 50.0,
            "unit": "kg",
            "min_stock_level": 10.0,
        },
    )

    # Assert
    assert response.status_code == 201
    json_data = response.json()
    assert json_data["id"] == 1
    assert json_data["name"] == "Farinha de Trigo"
    assert json_data["category"] == "RAW_MATERIAL"
    assert json_data["current_quantity_amount"] == 50.0
    assert json_data["current_quantity_unit"] == "kg"
    assert json_data["min_stock_level"] == 10.0
    assert json_data["is_active"] is True

    # Verify persistence
    repo = SQLAlchemyStockItemRepository(sqlite_session)
    persisted = await repo.find_by_id(1, "franquia_001")
    assert persisted is not None
    assert persisted.name == "Farinha de Trigo"


@pytest.mark.asyncio
async def test_create_stock_item_duplicate_name_returns_409(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
    # Arrange
    repo = SQLAlchemyStockItemRepository(sqlite_session)
    item = StockItem(
        id=5,
        tenant_id="franquia_001",
        name="Tomate",
        category=StockCategory.RAW_MATERIAL.value,
        current_quantity=MeasuredQuantity(10.0, MeasurementUnit.KILOGRAM),
    )
    await repo.save(item)
    await sqlite_session.commit()

    # Act
    response = await api_client.post(
        "/api/v1/stock/items",
        json={
            "id": 6,
            "name": "Tomate",
            "category": "RAW_MATERIAL",
            "current_quantity": 5.0,
            "unit": "kg",
        },
    )

    # Assert
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_list_stock_items_endpoint(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
    # Arrange — create via API so BackgroundTasks populate Mongo read model
    for sid, name, cat in [(10, "Arroz", "RAW_MATERIAL"), (11, "Feijão", "RAW_MATERIAL")]:
        resp = await api_client.post(
            "/api/v1/stock/items",
            json={"id": sid, "name": name, "category": cat, "current_quantity": 100.0, "unit": "kg"},
        )
        assert resp.status_code == 201

    # Act
    response = await api_client.get("/api/v1/stock/items")

    # Assert
    assert response.status_code == 200
    json_data = response.json()
    assert len(json_data) == 2
    names = {i["name"] for i in json_data}
    assert names == {"Arroz", "Feijão"}


@pytest.mark.asyncio
async def test_list_stock_items_low_stock_filter(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
    # Arrange — create via API so BackgroundTasks populate Mongo read model
    resp = await api_client.post(
        "/api/v1/stock/items",
        json={"id": 20, "name": "Leite", "category": "RAW_MATERIAL", "current_quantity": 2.0, "unit": "l", "min_stock_level": 10.0},
    )
    assert resp.status_code == 201
    resp = await api_client.post(
        "/api/v1/stock/items",
        json={"id": 21, "name": "Café", "category": "RAW_MATERIAL", "current_quantity": 15.0, "unit": "kg", "min_stock_level": 5.0},
    )
    assert resp.status_code == 201

    # Act
    response = await api_client.get("/api/v1/stock/items?low_stock_only=true")

    # Assert
    assert response.status_code == 200
    json_data = response.json()
    assert len(json_data) == 1
    assert json_data[0]["name"] == "Leite"
    assert json_data[0]["is_low_stock"] is True


@pytest.mark.asyncio
async def test_get_stock_item_endpoint(api_client: AsyncClient, sqlite_session: AsyncSession) -> None:
    # Arrange — create via API so BackgroundTasks populate Mongo read model
    resp = await api_client.post(
        "/api/v1/stock/items",
        json={"id": 30, "name": "Sal", "category": "RAW_MATERIAL", "current_quantity": 25.0, "unit": "kg"},
    )
    assert resp.status_code == 201

    # Act
    response = await api_client.get("/api/v1/stock/items/30")

    # Assert
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["id"] == 30
    assert json_data["name"] == "Sal"


@pytest.mark.asyncio
async def test_get_stock_item_not_found_returns_404(api_client: AsyncClient) -> None:
    # Act
    response = await api_client.get("/api/v1/stock/items/999")

    # Assert
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_add_stock_endpoint(api_client: AsyncClient, sqlite_session: AsyncSession) -> None:
    # Arrange
    repo = SQLAlchemyStockItemRepository(sqlite_session)
    item = StockItem(
        id=40,
        tenant_id="franquia_001",
        name="Óleo",
        category=StockCategory.RAW_MATERIAL.value,
        current_quantity=MeasuredQuantity(10.0, MeasurementUnit.LITER),
    )
    await repo.save(item)
    await sqlite_session.commit()

    # Act
    response = await api_client.post(
        "/api/v1/stock/items/40/add",
        json={"quantity": 5.0, "reason": "Compra semanal"},
    )

    # Assert
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["current_quantity_amount"] == 15.0


@pytest.mark.asyncio
async def test_deduct_stock_endpoint(api_client: AsyncClient, sqlite_session: AsyncSession) -> None:
    # Arrange
    repo = SQLAlchemyStockItemRepository(sqlite_session)
    item = StockItem(
        id=50,
        tenant_id="franquia_001",
        name="Carne Moída",
        category=StockCategory.RAW_MATERIAL.value,
        current_quantity=MeasuredQuantity(20.0, MeasurementUnit.KILOGRAM),
    )
    await repo.save(item)
    await sqlite_session.commit()

    # Act
    response = await api_client.post(
        "/api/v1/stock/items/50/deduct",
        json={"quantity": 5.0, "reason": "Consumo diário"},
    )

    # Assert
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["current_quantity_amount"] == 15.0


@pytest.mark.asyncio
async def test_deduct_stock_insufficient_returns_422(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
    # Arrange
    repo = SQLAlchemyStockItemRepository(sqlite_session)
    item = StockItem(
        id=55,
        tenant_id="franquia_001",
        name="Manteiga",
        category=StockCategory.RAW_MATERIAL.value,
        current_quantity=MeasuredQuantity(2.0, MeasurementUnit.KILOGRAM),
    )
    await repo.save(item)
    await sqlite_session.commit()

    # Act
    response = await api_client.post(
        "/api/v1/stock/items/55/deduct",
        json={"quantity": 10.0},
    )

    # Assert
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_set_min_stock_level_endpoint(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
    # Arrange
    repo = SQLAlchemyStockItemRepository(sqlite_session)
    item = StockItem(
        id=60,
        tenant_id="franquia_001",
        name="Papel Toalha",
        category=StockCategory.PACKAGING.value,
        current_quantity=MeasuredQuantity(50.0, MeasurementUnit.UNIT),
    )
    await repo.save(item)
    await sqlite_session.commit()

    # Act
    response = await api_client.put(
        "/api/v1/stock/items/60/min-level",
        json={"min_stock_level": 20.0},
    )

    # Assert
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["min_stock_level"] == 20.0


@pytest.mark.asyncio
async def test_adjust_stock_endpoint(api_client: AsyncClient, sqlite_session: AsyncSession) -> None:
    # Arrange
    repo = SQLAlchemyStockItemRepository(sqlite_session)
    item = StockItem(
        id=70,
        tenant_id="franquia_001",
        name="Detergente",
        category=StockCategory.SUPPLEMENT.value,
        current_quantity=MeasuredQuantity(10.0, MeasurementUnit.LITER),
    )
    await repo.save(item)
    await sqlite_session.commit()

    # Act
    response = await api_client.post(
        "/api/v1/stock/items/70/adjust",
        json={"new_quantity": 15.0, "reason": "Inventário mensal"},
    )

    # Assert
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["current_quantity_amount"] == 15.0


@pytest.mark.asyncio
async def test_get_stock_movements_endpoint(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
    # Arrange — create item and a movement via add stock
    repo = SQLAlchemyStockItemRepository(sqlite_session)
    item = StockItem(
        id=80,
        tenant_id="franquia_001",
        name="Refrigerante",
        category=StockCategory.BEVERAGE.value,
        current_quantity=MeasuredQuantity(48.0, MeasurementUnit.UNIT),
    )
    await repo.save(item)
    await sqlite_session.commit()

    await api_client.post("/api/v1/stock/items/80/add", json={"quantity": 12.0, "reason": "Reposição"})

    # Act
    response = await api_client.get("/api/v1/stock/items/80/movements")

    # Assert
    assert response.status_code == 200
    json_data = response.json()
    assert len(json_data) >= 1
    assert json_data[0]["stock_item_id"] == 80
    assert json_data[0]["movement_type"] == "INBOUND"
    assert json_data[0]["quantity_changed"] == 12.0
