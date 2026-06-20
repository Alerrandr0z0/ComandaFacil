from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from motor.motor_asyncio import AsyncIOMotorDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.domain.employee import Employee, RoleType
from app.auth.domain.session import Session
from app.auth.infrastructure.repositories import (
    SQLAlchemyEmployeeRepository,
    SQLAlchemySessionRepository,
    SQLAlchemyTenantRepository,
)
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
    db: DbSession, credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer)
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
    db: DbSession, session: Session = Depends(get_current_session)
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


async def get_current_admin_employee(
    current_employee: CurrentEmployee,
) -> Employee:
    """Dependency: gets the authenticated Employee and ensures they are a SUPER_ADMIN."""
    # Assuming role is checked by iterating roles. We might need a better way to check this
    # without needing a tenant context. For now, check if ANY active role is SUPER_ADMIN
    is_admin = any(
        role.role_type == RoleType.SUPER_ADMIN and role.is_active for role in current_employee.roles
    )
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requisição requer privilégios de administrador global.",
        )
    return current_employee


CurrentAdminEmployee = Annotated[Employee, Depends(get_current_admin_employee)]


def require_permission(action: str) -> Callable[..., Awaitable[Employee]]:
    """Dependency creator enforcing a specific employee permission strategy on the route."""

    async def dependency(
        current_employee: CurrentEmployee,
        tenant_id_str: CurrentTenantId,
        db: DbSession,
    ) -> Employee:
        try:
            tenant_id = int(tenant_id_str)
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid tenant ID format.",
            ) from err

        tenant_repo = SQLAlchemyTenantRepository(db)
        tenant = await tenant_repo.find_by_id(tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Franquia '{tenant_id}' não encontrada.",
            )
        if not tenant.is_active_tenant():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Franquia inativa.",
            )

        if not current_employee.permits(action, tenant):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Funcionário não possui permissão para executar esta ação: {action}",
            )
        return current_employee

    return dependency
