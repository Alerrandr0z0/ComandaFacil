from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.domain.employee import Employee
from app.auth.domain.session import Session
from app.auth.infrastructure.repositories import SQLAlchemySessionRepository, SQLAlchemyEmployeeRepository
from app.settings import Settings, get_settings
from app.shared.database import get_async_session, get_mongo_db
from app.shared.tenant_context import tenant_context_var


async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency: async SQLAlchemy session (PostgreSQL write DB)."""
    async for session in get_async_session():
        yield session


# Type aliases for cleaner dependency injection
DbSession = Annotated[AsyncSession, Depends(db_session)]


async def mongo_db() -> AsyncIOMotorDatabase:  # type: ignore[type-arg]
    """Dependency: Motor MongoDB database (read DB)."""
    return get_mongo_db()


MongoDB = Annotated[AsyncIOMotorDatabase, Depends(mongo_db)]  # type: ignore[type-arg]


def get_current_tenant_id() -> str:
    """Dependency: returns the current tenant_id from context."""
    tenant_id = tenant_context_var.get(None)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context not set. Provide X-Tenant-ID header.",
        )
    return tenant_id


CurrentTenantId = Annotated[str, Depends(get_current_tenant_id)]
AppSettings = Annotated[Settings, Depends(get_settings)]


http_bearer = HTTPBearer(auto_error=False)


async def get_current_session(
    db: DbSession,
    credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer)
) -> Session:
    """Dependency: gets and validates the current stateful session from database."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token missing.",
        )
    session_repo = SQLAlchemySessionRepository(db)
    session = await session_repo.find_by_id(credentials.credentials)
    if not session or session.is_expired():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session.",
        )
    return session


CurrentSession = Annotated[Session, Depends(get_current_session)]


async def get_current_employee(
    db: DbSession,
    session: Session = Depends(get_current_session)
) -> Employee:
    """Dependency: gets the authenticated Employee aggregate for the current session."""
    employee_repo = SQLAlchemyEmployeeRepository(db)
    employee = await employee_repo.find_by_id(session.employee_id)
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated employee not found.",
        )
    return employee


CurrentEmployee = Annotated[Employee, Depends(get_current_employee)]
