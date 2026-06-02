from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app.analytics.domain.value_objects import DashboardData
from app.dependencies import mongo_db
from app.main import app


class FakeCursor:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self._data = data

    async def to_list(self, length: int | None) -> list[dict[str, Any]]:
        return self._data


class FakeMongoCollection:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self._data = data

    def aggregate(self, pipeline: list[dict]) -> FakeCursor:
        return FakeCursor(self._data)

    async def count_documents(self, filter: dict) -> int:  # noqa: A002
        return 5


class FakeMongoDB:
    def __init__(self) -> None:
        self._dashboard_data: list[dict[str, Any]] = [
            {"total_sales": 2000.0, "orders_count": 50, "avg_ticket": 40.0}
        ]
        self._kitchen_data: list[dict[str, Any]] = []

    def __getitem__(self, name: str) -> FakeMongoCollection:
        if name == "orders_read":
            return FakeMongoCollection(self._dashboard_data)
        if name == "stock_read":
            return FakeMongoCollection([])
        if name == "kitchen_read":
            return FakeMongoCollection(self._kitchen_data)
        return FakeMongoCollection([])


@pytest.fixture
def fake_mongo() -> FakeMongoDB:
    return FakeMongoDB()


@pytest.fixture
async def api_client(fake_mongo: FakeMongoDB) -> AsyncClient:
    async def override_mongo() -> FakeMongoDB:
        return fake_mongo

    app.dependency_overrides[mongo_db] = override_mongo
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-Tenant-ID": "t1"},
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.unit
async def test_get_dashboard_when_data_exists_then_returns_200(
    api_client: AsyncClient,
) -> None:
    # Act
    response = await api_client.get("/api/v1/analytics/dashboard")

    # Assert
    assert response.status_code == 200
    body = response.json()
    assert body["orders_count"] == 50
    assert body["total_sales"] == "2000.0"
    assert body["average_ticket"] == "40.0"


@pytest.mark.unit
async def test_get_dashboard_when_no_data_then_returns_zeros(
    api_client: AsyncClient,
    fake_mongo: FakeMongoDB,
) -> None:
    # Arrange
    fake_mongo._dashboard_data = []  # noqa: SLF001
    fake_mongo._kitchen_data = []

    # Act
    response = await api_client.get("/api/v1/analytics/dashboard")

    # Assert
    assert response.status_code == 200
    body = response.json()
    assert body["orders_count"] == 0
    assert body["total_sales"] == "0"
    assert body["low_stock_items"] == 5
