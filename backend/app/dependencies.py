from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from app.settings import Settings, get_settings
from app.shared.database import get_async_session, get_mongo_db
from app.shared.tenant_context import tenant_context_var


async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency: async SQLAlchemy session (PostgreSQL write DB)."""
    async for session in get_async_session():
        yield session


async def mongo_db() -> AsyncIOMotorDatabase:  # type: ignore[type-arg]
    """Dependency: Motor MongoDB database (read DB)."""
    return get_mongo_db()


def get_current_tenant_id() -> str:
    """Dependency: returns the current tenant_id from context."""
    tenant_id = tenant_context_var.get(None)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context not set. Provide X-Tenant-ID header.",
        )
    return tenant_id


# Type aliases for cleaner dependency injection
DbSession = Annotated[AsyncSession, Depends(db_session)]
MongoDB = Annotated[AsyncIOMotorDatabase, Depends(mongo_db)]  # type: ignore[type-arg]
CurrentTenantId = Annotated[str, Depends(get_current_tenant_id)]
AppSettings = Annotated[Settings, Depends(get_settings)]
