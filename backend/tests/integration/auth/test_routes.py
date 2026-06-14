from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.domain.tenant import PlanType, Tenant
from app.auth.infrastructure.repositories import SQLAlchemyTenantRepository
from app.dependencies import db_session
from app.main import app
from app.shared.base_orm import Base

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


# Setup async sqlite engine for route integration tests
@pytest.fixture
async def sqlite_session() -> AsyncGenerator[AsyncSession, None]:
    from app.shared import database as _database

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    old_factory = _database.session_factory
    _database.session_factory = session_factory

    async with session_factory() as session:
        from app.shared.domain_events import EventBus, pending_events_var

        token = pending_events_var.set([])

        original_commit = session.commit

        async def commit_with_events() -> None:
            await original_commit()
            events = pending_events_var.get()
            if events:
                pending_events_var.set([])
                for event in events:
                    await EventBus.publish(event)

        session.commit = commit_with_events

        try:
            yield session
            await session.rollback()
        finally:
            pending_events_var.reset(token)

    _database.session_factory = old_factory
    await engine.dispose()


@pytest.fixture
async def api_client(sqlite_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Client overriding db_session dependency to use our temporary SQLite db."""

    async def override_db_session() -> AsyncGenerator[AsyncSession, None]:
        yield sqlite_session

    app.dependency_overrides[db_session] = override_db_session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", headers={"X-Tenant-ID": "10"}
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
            "password": "secure_password_123",
        },
    )

    # Assert
    assert response.status_code == 201
    json_data = response.json()
    assert json_data["id"] == 1
    assert json_data["name"] == "Jane Doe"
    assert json_data["email"] == "jane@comandafacil.com"


@pytest.mark.asyncio
async def test_assign_role_endpoint_success(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
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
            "password": "secure_password_123",
        },
    )

    # Act - Assign Role
    response = await api_client.post(
        "/api/v1/auth/employees/1/roles", json={"tenant_id": 10, "role_type": "WAITER"}
    )

    # Assert
    assert response.status_code == 200
    assert response.json() == {"detail": "Role assigned successfully"}


@pytest.mark.asyncio
async def test_login_endpoint_success(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
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
            "password": "secure_password_123",
        },
    )

    # Assign Role
    await api_client.post(
        "/api/v1/auth/employees/1/roles", json={"tenant_id": 10, "role_type": "WAITER"}
    )

    # Act - Login
    response = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "jane@comandafacil.com", "password": "secure_password_123", "tenant_id": 10},
    )

    # Assert
    assert response.status_code == 200
    json_data = response.json()
    assert "session_id" in json_data
    assert "expires_at" in json_data


@pytest.mark.asyncio
async def test_me_and_logout_endpoints_success(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
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
            "password": "secure_password_123",
        },
    )

    # Assign Role
    await api_client.post(
        "/api/v1/auth/employees/1/roles", json={"tenant_id": 10, "role_type": "WAITER"}
    )

    # Login to get session
    login_response = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "jane@comandafacil.com", "password": "secure_password_123", "tenant_id": 10},
    )
    session_id = login_response.json()["session_id"]

    # Act - Me query using Bearer token
    me_response = await api_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {session_id}"}
    )

    # Assert Me
    assert me_response.status_code == 200
    me_data = me_response.json()
    assert me_data["id"] == 1
    assert me_data["name"] == "Jane Doe"
    assert me_data["email"] == "jane@comandafacil.com"

    # Act - Logout using Bearer token
    logout_response = await api_client.post(
        "/api/v1/auth/logout", headers={"Authorization": f"Bearer {session_id}"}
    )

    # Assert Logout
    assert logout_response.status_code == 200
    assert logout_response.json() == {"detail": "Logged out successfully"}

    # Act - Me query after logout (should fail)
    me_after_logout = await api_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {session_id}"}
    )
    assert me_after_logout.status_code == 401


@pytest.mark.asyncio
async def test_toggle_active_employee_endpoint_success(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
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
            "password": "secure_password_123",
        },
    )

    # Assign Role
    await api_client.post(
        "/api/v1/auth/employees/1/roles", json={"tenant_id": 10, "role_type": "WAITER"}
    )

    # Act - Toggle active to deactivate
    response_deactivate = await api_client.post(
        "/api/v1/auth/employees/1/toggle-active", headers={"X-Tenant-ID": "10"}
    )
    assert response_deactivate.status_code == 200
    assert response_deactivate.json() == {"is_active": False}

    # Act - Toggle active to reactivate
    response_reactivate = await api_client.post(
        "/api/v1/auth/employees/1/toggle-active", headers={"X-Tenant-ID": "10"}
    )
    assert response_reactivate.status_code == 200
    assert response_reactivate.json() == {"is_active": True}


@pytest.mark.asyncio
async def test_delete_employee_endpoint_success(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
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
            "password": "secure_password_123",
        },
    )

    # Assign Role
    await api_client.post(
        "/api/v1/auth/employees/1/roles", json={"tenant_id": 10, "role_type": "WAITER"}
    )

    # Act - Delete employee role from tenant
    response = await api_client.delete("/api/v1/auth/employees/1", headers={"X-Tenant-ID": "10"})
    assert response.status_code == 200
    assert response.json() == {"detail": "Colaborador removido da franquia com sucesso."}


@pytest.mark.asyncio
async def test_list_audit_logs_endpoint_success(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
    # Arrange: Create a tenant and register/delete employee to trigger a log
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
            "password": "secure_password_123",
        },
    )
    # Assign Role
    await api_client.post(
        "/api/v1/auth/employees/1/roles", json={"tenant_id": 10, "role_type": "WAITER"}
    )
    # Delete employee (which generates audit log)
    delete_resp = await api_client.delete("/api/v1/auth/employees/1", headers={"X-Tenant-ID": "10"})
    assert delete_resp.status_code == 200

    # Act - Retrieve audit logs
    response = await api_client.get("/api/v1/auth/audit-logs", headers={"X-Tenant-ID": "10"})

    # Assert
    assert response.status_code == 200
    json_data = response.json()
    assert len(json_data) >= 1
    assert any(log["action"] == "EMPLOYEE_REMOVED" for log in json_data)


@pytest.mark.asyncio
async def test_order_and_kitchen_events_are_audited_successfully(
    api_client: AsyncClient, sqlite_session: AsyncSession
) -> None:
    from app.auth.application.audit_listener import register_audit_listeners
    from app.kitchen.domain.kitchen_events import KitchenItemStatusChanged
    from app.order.domain.order_events import OrderItemAdded
    from app.shared.domain_events import EventBus

    # Ensure listeners are registered
    register_audit_listeners()

    from decimal import Decimal

    # Trigger events
    event_order = OrderItemAdded(
        order_id=123,
        tenant_id="10",
        item_id=1,
        menu_item_id=456,
        name="Burger",
        quantity=2,
        price=Decimal("15.50"),
        notes="no onions",
    )
    event_kitchen = KitchenItemStatusChanged(
        item_id=789,
        tenant_id="10",
        correlation_id=1,
        name="Burger",
        old_state="WAITING",
        new_state="PREPARING",
    )

    await EventBus.publish(event_order)
    await EventBus.publish(event_kitchen)

    # Act - Retrieve audit logs
    response = await api_client.get("/api/v1/auth/audit-logs", headers={"X-Tenant-ID": "10"})

    # Assert
    assert response.status_code == 200
    json_data = response.json()
    assert len(json_data) >= 2

    actions = [log["action"] for log in json_data]
    assert "ORDER_ITEM_ADD" in actions
    assert "KITCHEN_STATUS_PREPARING" in actions
