from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import pytest
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from testcontainers.mongodb import MongoDbContainer

from app.analytics.domain.enums import AnalyticsPeriod
from app.analytics.infrastructure.mongo_repository import MongoAnalyticsRepository

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


@pytest.fixture(scope="module")
def mongo_container() -> Any:
    with MongoDbContainer("mongo:7-jammy") as mongo:
        yield mongo


@pytest.fixture
async def mongo_db(mongo_container: Any) -> AsyncGenerator[AsyncIOMotorDatabase[dict[str, Any]], None]:
    url = mongo_container.get_connection_url()
    client = AsyncIOMotorClient(url)
    db = client["test_analytics"]
    yield db
    await client.drop_database("test_analytics")
    client.close()


@pytest.fixture
async def seeded_db(mongo_db: AsyncIOMotorDatabase[dict[str, Any]]) -> AsyncIOMotorDatabase[dict[str, Any]]:
    # Seed orders_read with 3 orders
    orders = [
        {
            "tenant_id": "franquia_001",
            "order_id": 1,
            "total": 100.0,
            "items": [
                {"name": "Pizza", "category": "Pratos", "price": 60.0},
                {"name": "Suco", "category": "Bebidas", "price": 40.0},
            ],
            "created_at": datetime.now(UTC),
        },
        {
            "tenant_id": "franquia_001",
            "order_id": 2,
            "total": 50.0,
            "items": [
                {"name": "Salada", "category": "Pratos", "price": 50.0},
            ],
            "created_at": datetime.now(UTC),
        },
        {
            "tenant_id": "other_tenant",
            "order_id": 3,
            "total": 200.0,
            "items": [
                {"name": "Lasanha", "category": "Pratos", "price": 200.0},
            ],
            "created_at": datetime.now(UTC),
        },
    ]
    await mongo_db["orders_read"].insert_many(orders)

    # Seed kitchen_read
    kitchen_items = [
        {
            "tenant_id": "franquia_001",
            "item_id": 1,
            "state": "DONE",
            "started_at": datetime.now(UTC),
            "completed_at": datetime.now(UTC),
            "created_at": datetime.now(UTC),
        },
        {
            "tenant_id": "franquia_001",
            "item_id": 2,
            "state": "DONE",
            "started_at": datetime.now(UTC),
            "completed_at": datetime.now(UTC),
            "created_at": datetime.now(UTC),
        },
        {
            "tenant_id": "franquia_001",
            "item_id": 3,
            "state": "COOKING",
            "started_at": datetime.now(UTC),
            "completed_at": None,
            "created_at": datetime.now(UTC),
        },
    ]
    await mongo_db["kitchen_read"].insert_many(kitchen_items)

    # Seed stock_read
    stock_items = [
        {"tenant_id": "franquia_001", "name": "Tomate", "is_low_stock": True},
        {"tenant_id": "franquia_001", "name": "Cebola", "is_low_stock": False},
        {"tenant_id": "franquia_001", "name": "Alface", "is_low_stock": True},
    ]
    await mongo_db["stock_read"].insert_many(stock_items)

    return mongo_db


@pytest.mark.asyncio
async def test_get_dashboard_when_data_exists_then_returns_aggregated(seeded_db: Any) -> None:
    # Arrange
    repo = MongoAnalyticsRepository(seeded_db)

    # Act
    data = await repo.get_dashboard("franquia_001", AnalyticsPeriod.DAY)

    # Assert
    assert data.total_sales == Decimal("150")
    assert data.orders_count == 2
    assert data.average_ticket == Decimal("75")
    assert data.low_stock_items == 2
    assert data.average_prep_time_minutes >= 0


@pytest.mark.asyncio
async def test_get_dashboard_when_no_data_then_returns_zeros(seeded_db: Any) -> None:
    # Arrange
    repo = MongoAnalyticsRepository(seeded_db)

    # Act
    data = await repo.get_dashboard("nonexistent_tenant", AnalyticsPeriod.DAY)

    # Assert
    assert data.total_sales == Decimal("0")
    assert data.orders_count == 0
    assert data.average_ticket == Decimal("0")
    assert data.low_stock_items == 0
    assert data.average_prep_time_minutes == 0


@pytest.mark.asyncio
async def test_get_sales_report_when_data_exists_then_returns_aggregated(seeded_db: Any) -> None:
    # Arrange
    repo = MongoAnalyticsRepository(seeded_db)

    # Act
    data = await repo.get_sales_report("franquia_001", AnalyticsPeriod.DAY)

    # Assert
    assert data.period == AnalyticsPeriod.DAY
    assert data.total_sales == Decimal("150")
    assert data.total_orders == 2
    assert data.average_ticket == Decimal("75")
    assert len(data.by_category) == 2
    assert data.by_category.get("Pratos") == Decimal("110")
    assert data.by_category.get("Bebidas") == Decimal("40")


@pytest.mark.asyncio
async def test_get_order_insights_when_data_exists_then_returns_aggregated(seeded_db: Any) -> None:
    # Arrange
    repo = MongoAnalyticsRepository(seeded_db)

    # Act
    data = await repo.get_order_insights("franquia_001", AnalyticsPeriod.DAY)

    # Assert
    assert data.period == AnalyticsPeriod.DAY
    assert data.total_orders == 2
    assert data.average_items_per_order > 0
    assert 0 <= data.peak_hour <= 23


@pytest.mark.asyncio
async def test_get_kitchen_performance_when_data_exists_then_returns_aggregated(
    seeded_db: Any,
) -> None:
    # Arrange
    repo = MongoAnalyticsRepository(seeded_db)

    # Act
    data = await repo.get_kitchen_performance("franquia_001", AnalyticsPeriod.DAY)

    # Assert
    assert data.period == AnalyticsPeriod.DAY
    assert data.items_prepared == 3
    assert 0 <= data.completion_rate <= 1
    assert data.average_prep_time_minutes >= 0


@pytest.mark.asyncio
async def test_get_kitchen_performance_when_no_completed_then_zero_rate(seeded_db: Any) -> None:
    # Arrange — all items with no completed_at
    all_raw: list[dict[str, Any]] = [
        {
            "tenant_id": "no_done",
            "item_id": i,
            "state": "WAITING",
            "started_at": datetime.now(UTC),
            "completed_at": None,
            "created_at": datetime.now(UTC),
        }
        for i in range(3)
    ]
    await seeded_db["kitchen_read"].insert_many(all_raw)
    repo = MongoAnalyticsRepository(seeded_db)

    # Act
    data = await repo.get_kitchen_performance("no_done", AnalyticsPeriod.DAY)

    # Assert
    assert data.items_prepared == 3
    assert data.completion_rate == 0.0
