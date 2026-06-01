from __future__ import annotations

import datetime
from collections.abc import AsyncGenerator
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.dependencies import db_session
from app.shared.base_orm import Base
from app.auth.domain.tenant import Tenant, PlanType
from app.auth.infrastructure.repositories import SQLAlchemyTenantRepository


# Setup async sqlite engine for route integration tests
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
async def api_client(sqlite_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Client overriding db_session dependency to use our temporary SQLite db."""
    async def override_db_session() -> AsyncGenerator[AsyncSession, None]:
        yield sqlite_session

    app.dependency_overrides[db_session] = override_db_session
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"X-Tenant-ID": "10"}
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_register_employee_endpoint_success(api_client: AsyncClient) -> None:
    # Act
    response = await api_client.post(
        "/api/v1/auth/employees",
        json={
            "id": 1,
            "name": "Jane Doe",
            "email": "jane@comandafacil.com",
            "password": "secure_password_123"
        }
    )

    # Assert
    assert response.status_code == 201
    json_data = response.json()
    assert json_data["id"] == 1
    assert json_data["name"] == "Jane Doe"
    assert json_data["email"] == "jane@comandafacil.com"


@pytest.mark.asyncio
async def test_assign_role_endpoint_success(api_client: AsyncClient, sqlite_session: AsyncSession) -> None:
    # Arrange
    tenant_repo = SQLAlchemyTenantRepository(sqlite_session)
    tenant = Tenant(id=10, name="Main Franchise", plan_type=PlanType.PRO, is_active=True)
    await tenant_repo.save(tenant)
    await sqlite_session.commit()

    # Register employee
    await api_client.post(
        "/api/v1/auth/employees",
        json={
            "id": 1,
            "name": "Jane Doe",
            "email": "jane@comandafacil.com",
            "password": "secure_password_123"
        }
    )

    # Act - Assign Role
    response = await api_client.post(
        "/api/v1/auth/employees/1/roles",
        json={
            "tenant_id": 10,
            "role_type": "WAITER"
        }
    )

    # Assert
    assert response.status_code == 200
    assert response.json() == {"detail": "Role assigned successfully"}


@pytest.mark.asyncio
async def test_login_endpoint_success(api_client: AsyncClient, sqlite_session: AsyncSession) -> None:
    # Arrange
    tenant_repo = SQLAlchemyTenantRepository(sqlite_session)
    tenant = Tenant(id=10, name="Main Franchise", plan_type=PlanType.PRO, is_active=True)
    await tenant_repo.save(tenant)
    await sqlite_session.commit()

    # Register employee
    await api_client.post(
        "/api/v1/auth/employees",
        json={
            "id": 1,
            "name": "Jane Doe",
            "email": "jane@comandafacil.com",
            "password": "secure_password_123"
        }
    )

    # Assign Role
    await api_client.post(
        "/api/v1/auth/employees/1/roles",
        json={
            "tenant_id": 10,
            "role_type": "WAITER"
        }
    )

    # Act - Login
    response = await api_client.post(
        "/api/v1/auth/login",
        json={
            "email": "jane@comandafacil.com",
            "password": "secure_password_123",
            "tenant_id": 10
        }
    )

    # Assert
    assert response.status_code == 200
    json_data = response.json()
    assert "session_id" in json_data
    assert "expires_at" in json_data


@pytest.mark.asyncio
async def test_me_and_logout_endpoints_success(api_client: AsyncClient, sqlite_session: AsyncSession) -> None:
    # Arrange
    tenant_repo = SQLAlchemyTenantRepository(sqlite_session)
    tenant = Tenant(id=10, name="Main Franchise", plan_type=PlanType.PRO, is_active=True)
    await tenant_repo.save(tenant)
    await sqlite_session.commit()

    # Register employee
    await api_client.post(
        "/api/v1/auth/employees",
        json={
            "id": 1,
            "name": "Jane Doe",
            "email": "jane@comandafacil.com",
            "password": "secure_password_123"
        }
    )

    # Assign Role
    await api_client.post(
        "/api/v1/auth/employees/1/roles",
        json={
            "tenant_id": 10,
            "role_type": "WAITER"
        }
    )

    # Login to get session
    login_response = await api_client.post(
        "/api/v1/auth/login",
        json={
            "email": "jane@comandafacil.com",
            "password": "secure_password_123",
            "tenant_id": 10
        }
    )
    session_id = login_response.json()["session_id"]

    # Act - Me query using Bearer token
    me_response = await api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {session_id}"}
    )

    # Assert Me
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["id"] == 1
    assert me_data["name"] == "Jane Doe"
    assert me_data["email"] == "jane@comandafacil.com"

    # Act - Logout using Bearer token
    logout_response = await api_client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {session_id}"}
    )

    # Assert Logout
    assert logout_response.status_code == 200
    assert logout_response.json() == {"detail": "Logged out successfully"}

    # Act - Me query after logout (should fail)
    me_after_logout = await api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {session_id}"}
    )
    assert me_after_logout.status_code == 401
