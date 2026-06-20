import logging
from dataclasses import dataclass
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.auth.domain.tenant import Tenant, TenantRepository

logger = logging.getLogger(__name__)


@dataclass
class GetTenantsQuery:
    pass


async def handle_get_tenants(_query: GetTenantsQuery, repo: TenantRepository) -> list[Tenant]:
    logger.info("Executando consulta: GetTenantsQuery")
    results = await repo.find_all()
    logger.info("Resultado da consulta GetTenantsQuery: %s", results)
    return results


@dataclass
class GetGlobalAnalyticsQuery:
    limit: int = 5
    sort_by: str = "revenue"


async def handle_get_global_analytics(
    query: GetGlobalAnalyticsQuery, mongo_db: AsyncIOMotorDatabase[dict[str, Any]]
) -> list[dict[str, Any]]:
    logger.info(
        "Executando consulta: GetGlobalAnalyticsQuery(limit=%s, sort_by=%r)",
        query.limit,
        query.sort_by,
    )
    # Simple aggregation for revenue per tenant
    pipeline = [
        {"$group": {"_id": "$tenant_id", "total_revenue": {"$sum": "$total"}}},
        {"$sort": {"total_revenue": -1}},
        {"$limit": query.limit},
    ]
    cursor = mongo_db["orders_read"].aggregate(pipeline)
    results = await cursor.to_list(length=None)
    logger.info("Resultado da consulta GetGlobalAnalyticsQuery: %s", results)
    return results
