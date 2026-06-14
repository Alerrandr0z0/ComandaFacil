from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.dependencies import db_session
from app.main import app
from app.shared.base_orm import Base
from app.stock.domain.enums import StockCategory
from app.stock.domain.measured_quantity import MeasuredQuantity
from app.stock.domain.stock_item import SimpleStockItem
from app.stock.infrastructure.pg_repository import SQLAlchemyStockItemRepository
from tests.integration.conftest_helpers import make_mock_db

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


@pytest.fixture
async def sqlite_session() -> AsyncGenerator[AsyncSession, None]:
    from app.shared import database as _database

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    old_factory = _database.session_factory
    _database.session_factory = session_factory

    async with session_factory() as session:
        from app.shared.domain_events import EventBus, pending_events_var

        token = pending_events_var.set([])

        original_commit = session.commit

        async def commit_with_events() -> None:
            await original_commit()
            events = pending_events_var.get()
            if events:
                pending_events_var.set([])
                for event in events:
                    await EventBus.publish(event)

        session.commit = commit_with_events

        try:
            yield session
            await session.rollback()
        finally:
            pending_events_var.reset(token)

    _database.session_factory = old_factory
    await engine.dispose()


@pytest.fixture
async def api_client(sqlite_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    _store, mock_db = make_mock_db()

    async def override_db_session() -> AsyncGenerator[AsyncSession, None]:
        yield sqlite_session

    async def override_mongo_db() -> object:
        return mock_db

    from app.auth.domain.employee import Employee
    from app.dependencies import get_current_employee, mongo_db

    async def override_current_employee() -> Employee:
        from app.shared.value_objects import Email

        return Employee(
            id=1,
            name="Test Employee",
            email=Email("test@comandafacil.com"),
            password_hash="hashed_password",
        )

    app.dependency_overrides[db_session] = override_db_session
    app.dependency_overrides[mongo_db] = override_mongo_db
    app.dependency_overrides[get_current_employee] = override_current_employee
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
            "initial_cost_amount": 5.0,
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
    item = SimpleStockItem(
        id=5,
        tenant_id="franquia_001",
        name="Tomate",
        category=StockCategory.RAW_MATERIAL.value,
        unit="kg",
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
            "initial_cost_amount": 5.0,
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
            json={
                "id": sid,
                "name": name,
                "category": cat,
                "current_quantity": 100.0,
                "initial_cost_amount": 5.0,
                "unit": "kg",
            },
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
        json={
            "id": 20,
            "name": "Leite",
            "category": "RAW_MATERIAL",
            "current_quantity": 2.0,
            "initial_cost_amount": 5.0,
            "unit": "l",
            "min_stock_level": 10.0,
        },
    )
    assert resp.status_code == 201
    resp = await api_client.post(
        "/api/v1/stock/items",
        json={
            "id": 21,
            "name": "Café",
            "category": "RAW_MATERIAL",
            "current_quantity": 15.0,
            "initial_cost_amount": 5.0,
            "unit": "kg",
            "min_stock_level": 5.0,
        },
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
async def test_get_stock_item_endpoint(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
    # Arrange — create via API so BackgroundTasks populate Mongo read model
    resp = await api_client.post(
        "/api/v1/stock/items",
        json={
            "id": 30,
            "name": "Sal",
            "category": "RAW_MATERIAL",
            "current_quantity": 25.0,
            "initial_cost_amount": 5.0,
            "unit": "kg",
        },
    )
    assert resp.status_code == 201
    created_id = resp.json()["id"]

    # Act
    response = await api_client.get(f"/api/v1/stock/items/{created_id}")

    # Assert
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["id"] == created_id
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
    item = SimpleStockItem(
        id=40,
        tenant_id="franquia_001",
        name="Óleo",
        category=StockCategory.RAW_MATERIAL.value,
        unit="l",
    )
    await repo.save(item)
    await sqlite_session.commit()

    # Act
    response = await api_client.post(
        "/api/v1/stock/items/40/add",
        json={"quantity": 5.0, "cost_amount": 5.0, "reason": "Compra semanal"},
    )

    # Assert
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["current_quantity_amount"] == 5.0


@pytest.mark.asyncio
async def test_deduct_stock_endpoint(api_client: AsyncClient, sqlite_session: AsyncSession) -> None:
    # Arrange
    repo = SQLAlchemyStockItemRepository(sqlite_session)
    item = SimpleStockItem(
        id=50,
        tenant_id="franquia_001",
        name="Carne Moída",
        category=StockCategory.RAW_MATERIAL.value,
        unit="kg",
    )
    from app.stock.domain.enums import TransactionType
    from app.stock.domain.transaction import StockTransaction

    item.add_transaction(
        StockTransaction(
            0,
            MeasuredQuantity(Decimal("20.0"), "kg"),
            TransactionType.INPUT,
            cost_amount=Decimal("5.00"),
        )
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
    item = SimpleStockItem(
        id=55,
        tenant_id="franquia_001",
        name="Manteiga",
        category=StockCategory.RAW_MATERIAL.value,
        unit="kg",
    )
    from app.stock.domain.enums import TransactionType
    from app.stock.domain.transaction import StockTransaction

    item.add_transaction(
        StockTransaction(
            0,
            MeasuredQuantity(Decimal("2.0"), "kg"),
            TransactionType.INPUT,
            cost_amount=Decimal("5.00"),
        )
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
    item = SimpleStockItem(
        id=60,
        tenant_id="franquia_001",
        name="Papel Toalha",
        category=StockCategory.PACKAGING.value,
        unit="un",
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
    item = SimpleStockItem(
        id=70,
        tenant_id="franquia_001",
        name="Detergente",
        category=StockCategory.SUPPLEMENT.value,
        unit="l",
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
    item = SimpleStockItem(
        id=80,
        tenant_id="franquia_001",
        name="Refrigerante",
        category=StockCategory.BEVERAGE.value,
        unit="un",
    )
    await repo.save(item)
    await sqlite_session.commit()

    await api_client.post(
        "/api/v1/stock/items/80/add",
        json={"quantity": 12.0, "cost_amount": 5.0, "reason": "Reposição"},
    )

    # Act
    response = await api_client.get("/api/v1/stock/items/80/movements")

    # Assert
    assert response.status_code == 200
    json_data = response.json()
    assert len(json_data) >= 1
    assert json_data[0]["stock_item_id"] == 80
    assert json_data[0]["movement_type"] == "INPUT"
    assert json_data[0]["quantity_changed"] == 12.0


@pytest.mark.asyncio
async def test_update_stock_item_endpoint_success(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
    # Arrange
    repo = SQLAlchemyStockItemRepository(sqlite_session)
    item = SimpleStockItem(
        id=90,
        tenant_id="franquia_001",
        name="Quejo",
        category="RAW_MATERIAL",
        unit="g",
        min_stock_level=100.0,
    )
    await repo.save(item)
    await sqlite_session.commit()

    # Act
    response = await api_client.put(
        "/api/v1/stock/items/90",
        json={
            "name": "Queijo",
            "category": "RAW_MATERIAL",
            "unit": "kg",
            "min_stock_level": 5.0,
        },
    )

    # Assert
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["name"] == "Queijo"
    assert json_data["current_quantity_unit"] == "kg"
    assert json_data["min_stock_level"] == 5.0

    # Verify persistence
    persisted = await repo.find_by_id(90, "franquia_001")
    assert persisted is not None
    assert persisted.name == "Queijo"
    assert isinstance(persisted, SimpleStockItem)
    assert persisted.unit == "kg"


@pytest.mark.asyncio
async def test_delete_stock_item_endpoint_success(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
    # Arrange
    repo = SQLAlchemyStockItemRepository(sqlite_session)
    item = SimpleStockItem(
        id=91,
        tenant_id="franquia_001",
        name="Item Deletável",
        category="RAW_MATERIAL",
        unit="un",
    )
    await repo.save(item)
    await sqlite_session.commit()

    # Act
    response = await api_client.delete("/api/v1/stock/items/91")

    # Assert
    assert response.status_code == 204

    # Verify persistence
    persisted = await repo.find_by_id(91, "franquia_001")
    assert persisted is None


@pytest.mark.asyncio
async def test_consumed_by_endpoint(api_client: AsyncClient, sqlite_session: AsyncSession) -> None:
    # Arrange — create menu item, recipe, stock item
    repo = SQLAlchemyStockItemRepository(sqlite_session)
    item = SimpleStockItem(
        id=100,
        tenant_id="franquia_001",
        name="Queijo Especial",
        category="RAW_MATERIAL",
        unit="g",
    )
    await repo.save(item)
    await sqlite_session.commit()

    # Create recipe in sqlite_session
    from app.menu.infrastructure.orm_models import MenuItemORM
    from app.stock.infrastructure.orm_models import RecipeIngredientORM, RecipeORM

    # Seed MenuItem first
    m_item = MenuItemORM(
        id=200,
        tenant_id="franquia_001",
        name="Pizza de Queijo",
        description="Deliciosa",
        category_name="Pizza",
        base_price=Decimal("40.00"),
        station_type="GRILL",
        is_available=True,
    )
    sqlite_session.add(m_item)
    await sqlite_session.flush()

    recipe = RecipeORM(id=200, menu_item_id=200, tenant_id="franquia_001")
    sqlite_session.add(recipe)
    await sqlite_session.flush()

    ing = RecipeIngredientORM(
        recipe_id=200,
        stock_item_id=100,
        quantity_value=Decimal("150.0"),
        quantity_unit="g",
    )
    sqlite_session.add(ing)
    await sqlite_session.commit()

    # Act
    response = await api_client.get("/api/v1/stock/items/100/consumed-by")

    # Assert
    assert response.status_code == 200
    json_data = response.json()
    assert len(json_data) == 1
    assert json_data[0]["menu_item_name"] == "Pizza de Queijo"
    assert json_data[0]["quantity_value"] == 150.0


@pytest.mark.asyncio
async def test_get_recipe_endpoint_success(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
    # Arrange
    repo = SQLAlchemyStockItemRepository(sqlite_session)
    item = SimpleStockItem(
        id=101,
        tenant_id="franquia_001",
        name="Molho",
        category="RAW_MATERIAL",
        unit="ml",
    )
    await repo.save(item)

    from app.stock.infrastructure.orm_models import RecipeIngredientORM, RecipeORM

    recipe = RecipeORM(id=201, menu_item_id=201, tenant_id="franquia_001")
    sqlite_session.add(recipe)
    await sqlite_session.flush()

    ing = RecipeIngredientORM(
        recipe_id=201,
        stock_item_id=101,
        quantity_value=Decimal("50.0"),
        quantity_unit="ml",
    )
    sqlite_session.add(ing)
    await sqlite_session.commit()

    # Act
    response = await api_client.get("/api/v1/stock/recipes/201")

    # Assert
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["menu_item_id"] == 201
    assert len(json_data["ingredients"]) == 1
    assert json_data["ingredients"][0]["stock_item_id"] == 101


@pytest.mark.asyncio
async def test_get_recipe_not_found(api_client: AsyncClient) -> None:
    # Act
    response = await api_client.get("/api/v1/stock/recipes/9999")
    # Assert
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_save_recipe_endpoint(api_client: AsyncClient, sqlite_session: AsyncSession) -> None:
    # Arrange
    repo = SQLAlchemyStockItemRepository(sqlite_session)
    item = SimpleStockItem(
        id=102,
        tenant_id="franquia_001",
        name="Ingrediente A",
        category="RAW_MATERIAL",
        unit="un",
    )
    await repo.save(item)
    await sqlite_session.commit()

    # Act
    response = await api_client.put(
        "/api/v1/stock/recipes/202",
        json={
            "ingredients": [{"stock_item_id": 102, "quantity_value": 2.0, "quantity_unit": "un"}]
        },
    )

    # Assert
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["menu_item_id"] == 202
    assert len(json_data["ingredients"]) == 1
    assert json_data["ingredients"][0]["stock_item_id"] == 102


@pytest.mark.asyncio
async def test_produce_recipe_endpoint_success(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
    # Arrange: stock item, menu item, recipe, and input transaction to have stock balance
    repo = SQLAlchemyStockItemRepository(sqlite_session)
    item = SimpleStockItem(
        id=103,
        tenant_id="franquia_001",
        name="Ingrediente B",
        category="RAW_MATERIAL",
        unit="un",
    )
    from app.stock.domain.enums import TransactionType
    from app.stock.domain.transaction import StockTransaction

    item.add_transaction(
        StockTransaction(
            0,
            MeasuredQuantity(Decimal("10.0"), "un"),
            TransactionType.INPUT,
            cost_amount=Decimal("2.50"),
        )
    )
    await repo.save(item)
    await sqlite_session.commit()

    # Seed MenuItem first
    from app.menu.infrastructure.orm_models import MenuItemORM
    from app.stock.infrastructure.orm_models import RecipeIngredientORM, RecipeORM

    m_item = MenuItemORM(
        id=203,
        tenant_id="franquia_001",
        name="Prato Especial",
        description="Delicia",
        category_name="Pratos",
        base_price=Decimal("15.00"),
        station_type="GRILL",
        is_available=True,
    )
    sqlite_session.add(m_item)
    await sqlite_session.flush()

    recipe = RecipeORM(id=203, menu_item_id=203, tenant_id="franquia_001")
    sqlite_session.add(recipe)
    await sqlite_session.flush()

    ing = RecipeIngredientORM(
        recipe_id=203,
        stock_item_id=103,
        quantity_value=Decimal("2.0"),
        quantity_unit="un",
    )
    sqlite_session.add(ing)
    await sqlite_session.commit()

    # Act
    response = await api_client.post("/api/v1/stock/recipes/203/produce?quantity=2")

    # Assert
    assert response.status_code == 200
    json_data = response.json()
    assert "203" in json_data["detail"]
    assert len(json_data["deducted_ingredients"]) == 1
    assert json_data["deducted_ingredients"][0]["stock_item_id"] == 103
    assert json_data["deducted_ingredients"][0]["quantity_deducted"] == 2.0

    # Verify stock deducted: 10 - (2 * 2) = 6
    updated_item = await repo.find_by_id(103, "franquia_001")
    assert updated_item is not None
    assert updated_item.get_balance().value == Decimal("6.0")


@pytest.mark.asyncio
async def test_produce_recipe_endpoint_insufficient_stock(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
    # Arrange: stock item with low balance, menu item, recipe
    repo = SQLAlchemyStockItemRepository(sqlite_session)
    item = SimpleStockItem(
        id=104,
        tenant_id="franquia_001",
        name="Ingrediente C",
        category="RAW_MATERIAL",
        unit="un",
    )
    from app.stock.domain.enums import TransactionType
    from app.stock.domain.transaction import StockTransaction

    item.add_transaction(
        StockTransaction(
            0,
            MeasuredQuantity(Decimal("1.0"), "un"),
            TransactionType.INPUT,
            cost_amount=Decimal("2.50"),
        )
    )
    await repo.save(item)
    await sqlite_session.commit()

    from app.menu.infrastructure.orm_models import MenuItemORM
    from app.stock.infrastructure.orm_models import RecipeIngredientORM, RecipeORM

    m_item = MenuItemORM(
        id=204,
        tenant_id="franquia_001",
        name="Prato Rápido",
        description="Delicia",
        category_name="Pratos",
        base_price=Decimal("15.00"),
        station_type="GRILL",
        is_available=True,
    )
    sqlite_session.add(m_item)
    await sqlite_session.flush()

    recipe = RecipeORM(id=204, menu_item_id=204, tenant_id="franquia_001")
    sqlite_session.add(recipe)
    await sqlite_session.flush()

    ing = RecipeIngredientORM(
        recipe_id=204,
        stock_item_id=104,
        quantity_value=Decimal("2.0"),
        quantity_unit="un",
    )
    sqlite_session.add(ing)
    await sqlite_session.commit()

    # Act: try to produce 1 portion (needs 2.0 un, but only has 1.0 un)
    response = await api_client.post("/api/v1/stock/recipes/204/produce")

    # Assert
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_stock_item_not_found(api_client: AsyncClient) -> None:
    response = await api_client.put(
        "/api/v1/stock/items/9999",
        json={
            "name": "Nonexistent",
            "category": "RAW_MATERIAL",
            "unit": "un",
            "min_stock_level": 1.0,
        },
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_stock_item_name_conflict(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
    repo = SQLAlchemyStockItemRepository(sqlite_session)
    item1 = SimpleStockItem(
        id=901, tenant_id="franquia_001", name="Item A", category="RAW_MATERIAL", unit="un"
    )
    item2 = SimpleStockItem(
        id=902, tenant_id="franquia_001", name="Item B", category="RAW_MATERIAL", unit="un"
    )
    await repo.save(item1)
    await repo.save(item2)
    await sqlite_session.commit()

    response = await api_client.put(
        "/api/v1/stock/items/901",
        json={
            "name": "Item B",
            "category": "RAW_MATERIAL",
            "unit": "un",
            "min_stock_level": 1.0,
        },
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_update_stock_item_unit_conversion(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
    repo = SQLAlchemyStockItemRepository(sqlite_session)
    item = SimpleStockItem(
        id=903, tenant_id="franquia_001", name="Item C", category="RAW_MATERIAL", unit="g"
    )
    from app.stock.domain.enums import TransactionType
    from app.stock.domain.transaction import StockTransaction

    item.add_transaction(
        StockTransaction(
            0,
            MeasuredQuantity(Decimal("100.0"), "g"),
            TransactionType.INPUT,
            cost_amount=Decimal("1.50"),
        )
    )
    await repo.save(item)
    await sqlite_session.commit()

    response = await api_client.put(
        "/api/v1/stock/items/903",
        json={
            "name": "Item C",
            "category": "RAW_MATERIAL",
            "unit": "kg",
            "min_stock_level": 1.0,
        },
    )
    assert response.status_code == 200
    assert response.json()["current_quantity_unit"] == "kg"


@pytest.mark.asyncio
async def test_delete_stock_item_not_found(api_client: AsyncClient) -> None:
    response = await api_client.delete("/api/v1/stock/items/9999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_add_stock_item_not_found_on_reload(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
    # Trigger 404 when item is not found (using a random non-existent item id)
    response = await api_client.post(
        "/api/v1/stock/items/9999/add",
        json={"quantity": 5.0, "cost_amount": 5.0, "reason": "Compra"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_deduct_stock_item_not_found_on_reload(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
    response = await api_client.post(
        "/api/v1/stock/items/9999/deduct",
        json={"quantity": 5.0, "reason": "Consumo"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_set_min_stock_level_item_not_found(api_client: AsyncClient) -> None:
    response = await api_client.put(
        "/api/v1/stock/items/9999/min-level",
        json={"min_stock_level": 20.0},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_adjust_stock_item_not_found(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/api/v1/stock/items/9999/adjust",
        json={"new_quantity": 15.0, "reason": "Inventário"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_adjust_stock_invalid_tx_type(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
    # First create an item
    repo = SQLAlchemyStockItemRepository(sqlite_session)
    item = SimpleStockItem(
        id=701,
        tenant_id="franquia_001",
        name="Detergente B",
        category=StockCategory.SUPPLEMENT.value,
        unit="l",
    )
    await repo.save(item)
    await sqlite_session.commit()

    response = await api_client.post(
        "/api/v1/stock/items/701/adjust",
        json={"new_quantity": 15.0, "reason": "Inventário", "transaction_type": "INVALID_TYPE"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_save_recipe_nonexistent_stock_item(api_client: AsyncClient) -> None:
    response = await api_client.put(
        "/api/v1/stock/recipes/202",
        json={
            "ingredients": [{"stock_item_id": 9999, "quantity_value": 2.0, "quantity_unit": "un"}]
        },
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_produce_recipe_nonexistent_recipe(api_client: AsyncClient) -> None:
    response = await api_client.post("/api/v1/stock/recipes/9999/produce")
    assert response.status_code == 200
    json_data = response.json()
    assert "9999" in json_data["detail"]
    assert len(json_data["deducted_ingredients"]) == 0


@pytest.mark.asyncio
async def test_stock_adjust_generates_audit_log(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
    # Arrange
    repo = SQLAlchemyStockItemRepository(sqlite_session)
    item = SimpleStockItem(
        id=750,
        tenant_id="franquia_001",
        name="Tomate Cereja",
        category="RAW_MATERIAL",
        unit="kg",
        min_stock_level=5.0,
    )
    await repo.save(item)
    await sqlite_session.commit()

    # Act - Perform stock adjustment
    response = await api_client.post(
        "/api/v1/stock/items/750/adjust",
        json={"new_quantity": 25.0, "reason": "Contagem Mensal", "transaction_type": "ADJUSTMENT"},
    )
    assert response.status_code == 200

    # Assert: Verify that an audit log was successfully written
    from sqlalchemy import select

    from app.auth.infrastructure.orm_models import AuditLogORM

    stmt = select(AuditLogORM).where(AuditLogORM.action == "STOCK_ADJUST")
    res = await sqlite_session.execute(stmt)
    logs = res.scalars().all()
    assert len(logs) == 1
    assert logs[0].entity_id == "750"
    assert "Tomate Cereja" in logs[0].details
    assert "Contagem Mensal" in logs[0].details
