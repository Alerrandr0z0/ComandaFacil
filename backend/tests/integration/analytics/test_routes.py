from __future__ import annotations

import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import pytest
from httpx import ASGITransport, AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.mongodb import MongoDbContainer

from app.dependencies import db_session, mongo_db
from app.main import app
from app.shared.base_orm import Base
from app.stock.domain.enums import StockCategory
from app.stock.domain.measured_quantity import MeasuredQuantity
from app.stock.domain.recipe import Recipe
from app.stock.domain.stock_item import SimpleStockItem
from app.stock.infrastructure.pg_repository import (
    SQLAlchemyRecipeRepository,
    SQLAlchemyStockItemRepository,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


@pytest.fixture(scope="module")
def mongo_container() -> Any:
    with MongoDbContainer("mongo:7-jammy") as mongo:
        yield mongo


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
async def api_client(
    sqlite_session: AsyncSession, mongo_container: Any
) -> AsyncGenerator[AsyncClient, None]:
    url = mongo_container.get_connection_url()
    client = AsyncIOMotorClient(url)
    mock_mongo = client["test_analytics_routes"]

    async def override_db_session() -> AsyncGenerator[AsyncSession, None]:
        yield sqlite_session

    async def override_mongo_db() -> object:
        return mock_mongo

    app.dependency_overrides[db_session] = override_db_session
    app.dependency_overrides[mongo_db] = override_mongo_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-Tenant-ID": "franquia_001"},
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
    await client.drop_database("test_analytics_routes")
    client.close()


@pytest.mark.asyncio
async def test_analytics_menu_matrix_route(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
    # 1. Setup StockItems and Recipe in SQLite DB
    item_repo = SQLAlchemyStockItemRepository(sqlite_session)
    recipe_repo = SQLAlchemyRecipeRepository(sqlite_session, item_repo)

    ingredient = SimpleStockItem(
        id=201,
        tenant_id="franquia_001",
        name="Ingrediente A",
        category=StockCategory.RAW_MATERIAL.value,
        unit="kg",
    )
    # Add an input transaction to give it unit cost
    from app.stock.domain.transaction import StockTransaction, TransactionType

    ingredient.add_transaction(
        StockTransaction(
            id=1,
            type=TransactionType.INPUT,
            quantity=MeasuredQuantity(Decimal("10.0"), "kg"),
            cost_amount=Decimal("50.0"),  # Unit cost = 5.0
            occurred_at=datetime.datetime.now(datetime.UTC),
        )
    )
    await item_repo.save(ingredient)

    recipe = Recipe(id=301, menu_item_id=1001, tenant_id="franquia_001")
    recipe.add_ingredient(ingredient, MeasuredQuantity(Decimal("2.0"), "kg"))  # Cost = 10.0
    await recipe_repo.save(recipe)
    await sqlite_session.commit()

    # 2. Setup Order read model in Mongo
    mongo = await app.dependency_overrides[mongo_db]()
    orders_coll = mongo["orders_read"]
    await orders_coll.insert_one(
        {
            "tenant_id": "franquia_001",
            "order_id": 1,
            "total": 50.0,
            "items": [
                {
                    "name": "Prato Especial",
                    "category": "GRILL",
                    "price": 25.0,
                    "menu_item_id": 1001,
                    "quantity": 2,
                    "subtotal": 50.0,
                }
            ],
            "created_at": datetime.datetime.now(datetime.UTC),
        }
    )

    # 3. Request /analytics/menu-matrix
    resp = await api_client.get("/api/v1/analytics/menu-matrix?period=day")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["menu_item_id"] == 1001
    assert item["name"] == "Prato Especial"
    assert item["quantity"] == 2
    assert item["cost"] == 100.0
    assert item["avg_price"] == 25.0
    assert item["margin"] == -75.0
    assert item["classification"] == "STAR"
