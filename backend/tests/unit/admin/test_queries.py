import logging
from typing import Any

import pytest

from app.admin.application.queries import (
    GetGlobalAnalyticsQuery,
    GetTenantsQuery,
    handle_get_global_analytics,
    handle_get_tenants,
)
from app.auth.domain.tenant import PlanType, Tenant, TenantRepository


class InMemoryTenantRepository(TenantRepository):
    def __init__(self) -> None:
        self._tenants: dict[int, Tenant] = {}

    async def find_by_id(self, id: int) -> Tenant | None:
        return self._tenants.get(id)

    async def find_all(self) -> list[Tenant]:
        return list(self._tenants.values())

    async def delete(self, id: int) -> None:
        if id in self._tenants:
            del self._tenants[id]

    async def save(self, tenant: Tenant) -> None:
        self._tenants[tenant.id] = tenant


class MockCursor:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data

    async def to_list(self, length: int | None = None) -> list[dict[str, Any]]:
        return self.data


class MockCollection:
    def __init__(self, aggregate_data: list[dict[str, Any]]) -> None:
        self.aggregate_data = aggregate_data

    def aggregate(self, pipeline: list[dict[str, Any]]) -> MockCursor:
        return MockCursor(self.aggregate_data)


class MockAsyncIOMotorDatabase:
    def __init__(self, aggregate_data: list[dict[str, Any]]) -> None:
        self.aggregate_data = aggregate_data

    def __getitem__(self, name: str) -> MockCollection:
        return MockCollection(self.aggregate_data)


@pytest.mark.asyncio()
async def test_handle_get_tenants_logs_query_and_results(caplog: pytest.LogCaptureFixture) -> None:
    repo = InMemoryTenantRepository()
    tenant = Tenant(id=1, name="Test Tenant", plan_type=PlanType.BASIC)
    await repo.save(tenant)

    query = GetTenantsQuery()
    with caplog.at_level(logging.INFO):
        results = await handle_get_tenants(query, repo)

    assert results == [tenant]
    assert any(
        "Executando consulta: GetTenantsQuery" in record.message for record in caplog.records
    )
    assert any(
        "Resultado da consulta GetTenantsQuery:" in record.message for record in caplog.records
    )
    assert any("Test Tenant" in record.message for record in caplog.records)


@pytest.mark.asyncio()
async def test_handle_get_global_analytics_logs_query_and_results(
    caplog: pytest.LogCaptureFixture,
) -> None:
    aggregate_data = [{"_id": "tenant_1", "total_revenue": 500.0}]
    mongo_db = MockAsyncIOMotorDatabase(aggregate_data)

    query = GetGlobalAnalyticsQuery(limit=5, sort_by="revenue")
    with caplog.at_level(logging.INFO):
        results = await handle_get_global_analytics(query, mongo_db)  # type: ignore

    assert results == aggregate_data
    assert any(
        "Executando consulta: GetGlobalAnalyticsQuery(limit=5, sort_by='revenue')" in record.message
        for record in caplog.records
    )
    assert any(
        "Resultado da consulta GetGlobalAnalyticsQuery:" in record.message
        for record in caplog.records
    )
    assert any("tenant_1" in record.message for record in caplog.records)
