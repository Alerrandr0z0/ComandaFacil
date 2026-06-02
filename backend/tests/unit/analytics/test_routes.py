from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


class FakeCursor:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self._data = data

    async def to_list(self, length: int | None) -> list[dict[str, Any]]:
        return self._data


class FakeMongoCollection:
    def __init__(self, *data_batches: list[dict[str, Any]]) -> None:
        self._batches = list(data_batches) if data_batches else [[]]
        self._call_count = 0
        self.count = 5

    def aggregate(self, pipeline: list[dict[str, Any]]) -> FakeCursor:
        idx = min(self._call_count, len(self._batches) - 1)
        self._call_count += 1
        return FakeCursor(self._batches[idx])

    async def count_documents(self, filter: dict[str, Any]) -> int:
        return self.count


class FakeMongoDB:
    def __init__(self) -> None:
        self._collections: dict[str, FakeMongoCollection] = {}

    def set_data(self, collection: str, *data_batches: list[dict[str, Any]]) -> None:
        self._collections[collection] = FakeMongoCollection(*data_batches)

    def set_count(self, collection: str, count: int) -> None:
        self._collections.setdefault(collection, FakeMongoCollection()).count = count

    def __getitem__(self, name: str) -> FakeMongoCollection:
        return self._collections.get(name, FakeMongoCollection())


def _build_app(fake_mongo: FakeMongoDB) -> FastAPI:
    from app.analytics.api.routes import router
    from app.dependencies import get_current_tenant_id, mongo_db

    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1")

    async def override_mongo() -> FakeMongoDB:
        return fake_mongo

    def override_tenant_id() -> str:
        return "t1"

    test_app.dependency_overrides[mongo_db] = override_mongo
    test_app.dependency_overrides[get_current_tenant_id] = override_tenant_id
    return test_app


@pytest.fixture
def fake_mongo() -> FakeMongoDB:
    db = FakeMongoDB()
    db.set_data(
        "orders_read",
        [{"total_sales": 2000.0, "orders_count": 50, "avg_ticket": 40.0}],
    )
    db.set_data("stock_read", [{}])
    db.set_data("kitchen_read", [])
    return db


@pytest.fixture
async def api_client(fake_mongo: FakeMongoDB):
    app = _build_app(fake_mongo)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ─── Dashboard ────────────────────────────────────────────────────────────────


@pytest.mark.unit
async def test_get_dashboard_when_data_exists_then_returns_200(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/analytics/dashboard")

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
    fake_mongo.set_data("orders_read", [])
    fake_mongo.set_data("kitchen_read", [])
    fake_mongo.set_count("stock_read", 0)

    response = await api_client.get("/api/v1/analytics/dashboard")

    assert response.status_code == 200
    body = response.json()
    assert body["orders_count"] == 0
    assert body["total_sales"] == "0"
    assert body["low_stock_items"] == 0


@pytest.mark.unit
async def test_get_dashboard_when_period_param_then_200(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/analytics/dashboard?period=week")

    assert response.status_code == 200


# ─── Sales ────────────────────────────────────────────────────────────────────


@pytest.mark.unit
async def test_get_sales_when_data_exists_then_returns_200(
    api_client: AsyncClient,
    fake_mongo: FakeMongoDB,
) -> None:
    fake_mongo.set_data(
        "orders_read",
        [{"total_sales": 5000.0, "total_orders": 120, "avg_ticket": 41.67}],
        [{"_id": "BEBIDAS", "total": 1500.0}],
    )

    response = await api_client.get("/api/v1/analytics/sales")

    assert response.status_code == 200
    body = response.json()
    assert body["period"] == "day"
    assert body["total_sales"] == "5000.0"
    assert body["total_orders"] == 120
    assert body["by_category"] == {"BEBIDAS": "1500.0"}


@pytest.mark.unit
async def test_get_sales_when_period_month_then_reflected(
    api_client: AsyncClient,
    fake_mongo: FakeMongoDB,
) -> None:
    fake_mongo.set_data(
        "orders_read",
        [{"total_sales": 5000.0, "total_orders": 120, "avg_ticket": 41.67}],
        [{"_id": "BEBIDAS", "total": 1500.0}],
    )

    response = await api_client.get("/api/v1/analytics/sales?period=month")

    assert response.status_code == 200
    assert response.json()["period"] == "month"


@pytest.mark.unit
async def test_get_sales_when_invalid_period_then_422(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/analytics/sales?period=invalid")

    assert response.status_code == 422


# ─── Orders ───────────────────────────────────────────────────────────────────


@pytest.mark.unit
async def test_get_orders_when_data_exists_then_returns_200(
    api_client: AsyncClient,
    fake_mongo: FakeMongoDB,
) -> None:
    fake_mongo.set_data("orders_read", [{"total_orders": 350, "avg_items": 2.4, "peak_hour": 19}])

    response = await api_client.get("/api/v1/analytics/orders")

    assert response.status_code == 200
    body = response.json()
    assert body["period"] == "day"
    assert body["total_orders"] == 350
    assert body["average_items_per_order"] == 2.4
    assert body["peak_hour"] == 19


@pytest.mark.unit
async def test_get_orders_when_period_week_then_reflected(
    api_client: AsyncClient,
    fake_mongo: FakeMongoDB,
) -> None:
    fake_mongo.set_data("orders_read", [{"total_orders": 350, "avg_items": 2.4, "peak_hour": 19}])

    response = await api_client.get("/api/v1/analytics/orders?period=week")

    assert response.status_code == 200
    assert response.json()["period"] == "week"


# ─── Kitchen ──────────────────────────────────────────────────────────────────


@pytest.mark.unit
async def test_get_kitchen_when_data_exists_then_returns_200(
    api_client: AsyncClient,
    fake_mongo: FakeMongoDB,
) -> None:
    fake_mongo.set_data(
        "kitchen_read",
        [{"avg_prep_time": 480000.0, "total_prepared": 50, "completed": 48}],
    )

    response = await api_client.get("/api/v1/analytics/kitchen")

    assert response.status_code == 200
    body = response.json()
    assert body["period"] == "day"
    assert "average_prep_time_minutes" in body
    assert "items_prepared" in body
    assert "completion_rate" in body


@pytest.mark.unit
async def test_get_kitchen_when_no_data_then_returns_zeros(
    api_client: AsyncClient,
    fake_mongo: FakeMongoDB,
) -> None:
    fake_mongo.set_data(
        "orders_read", [{"total_sales": 2000.0, "orders_count": 50, "avg_ticket": 40.0}]
    )
    fake_mongo.set_data("kitchen_read", [])

    response = await api_client.get("/api/v1/analytics/kitchen")

    assert response.status_code == 200
    body = response.json()
    assert body["average_prep_time_minutes"] == 0.0
    assert body["items_prepared"] == 0


# ─── Auth / Error handling ───────────────────────────────────────────────────


@pytest.mark.unit
async def test_analytics_when_no_tenant_id_then_400() -> None:
    from app.analytics.api.routes import router

    test_app = FastAPI()
    test_app.include_router(router, prefix="/api/v1")
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/analytics/dashboard")

    assert response.status_code == 400
