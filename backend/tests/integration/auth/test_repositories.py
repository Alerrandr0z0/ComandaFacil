from __future__ import annotations

import datetime
from collections.abc import AsyncGenerator
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.auth.domain.employee import Employee, RoleType
from app.auth.domain.tenant import Tenant, PlanType
from app.auth.domain.session import Session
from app.auth.infrastructure.repositories import (
    SQLAlchemyTenantRepository,
    SQLAlchemyEmployeeRepository,
    SQLAlchemySessionRepository,
)
from app.shared.base_orm import Base
from app.shared.value_objects import Email


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Async session fixture utilizing in-memory SQLite for extremely fast integration tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    
    # Create all tables in the SQLite database
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session
        await session.rollback()
        
    await engine.dispose()


@pytest.mark.asyncio
async def test_tenant_repository_lifecycle(db_session: AsyncSession) -> None:
    repo = SQLAlchemyTenantRepository(db_session)
    
    # 1. Save new tenant
    tenant = Tenant(id=1, name="ComandaFacil Central", plan_type=PlanType.PRO, is_active=True)
    await repo.save(tenant)
    await db_session.commit()
    
    # 2. Find tenant
    retrieved = await repo.find_by_id(1)
    assert retrieved is not None
    assert retrieved.id == 1
    assert retrieved.name == "ComandaFacil Central"
    assert retrieved.plan_type == PlanType.PRO
    assert retrieved.is_active is True
    
    # 3. Update tenant
    retrieved.name = "ComandaFacil Atualizado"
    retrieved.deactivate()
    await repo.save(retrieved)
    await db_session.commit()
    
    # 4. Verify update
    updated = await repo.find_by_id(1)
    assert updated is not None
    assert updated.name == "ComandaFacil Atualizado"
    assert updated.is_active is False


@pytest.mark.asyncio
async def test_employee_repository_lifecycle(db_session: AsyncSession) -> None:
    tenant_repo = SQLAlchemyTenantRepository(db_session)
    emp_repo = SQLAlchemyEmployeeRepository(db_session)
    
    # Set up Tenant
    tenant = Tenant(id=1, name="Franquia 1", plan_type=PlanType.BASIC, is_active=True)
    await tenant_repo.save(tenant)
    
    # 1. Create and save new employee
    email = Email("cashier@comandafacil.com")
    employee = Employee(id=1, name="Jane Cashier", email=email, password_hash="hash_value")
    employee.add_role(tenant, RoleType.CASHIER)
    
    await emp_repo.save(employee)
    await db_session.commit()
    
    # 2. Retrieve by ID
    retrieved = await emp_repo.find_by_id(1)
    assert retrieved is not None
    assert retrieved.id == 1
    assert retrieved.name == "Jane Cashier"
    assert retrieved.email == email
    assert len(retrieved.roles) == 1
    
    # 3. Retrieve by Email
    retrieved_email = await emp_repo.find_by_email(email)
    assert retrieved_email is not None
    assert retrieved_email.id == 1
    
    # 4. Modify role and check persistence
    with pytest.raises(Exception):
        retrieved.add_role(tenant, RoleType.MANAGER)


@pytest.mark.asyncio
async def test_session_repository_lifecycle(db_session: AsyncSession) -> None:
    tenant_repo = SQLAlchemyTenantRepository(db_session)
    emp_repo = SQLAlchemyEmployeeRepository(db_session)
    session_repo = SQLAlchemySessionRepository(db_session)
    
    # Set up dependencies
    tenant = Tenant(id=1, name="Franquia 1", plan_type=PlanType.BASIC, is_active=True)
    await tenant_repo.save(tenant)
    
    email = Email("waiter@comandafacil.com")
    employee = Employee(id=1, name="John Waiter", email=email, password_hash="hash")
    await emp_repo.save(employee)
    
    await db_session.commit()
    
    # 1. Save Session
    expires = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=2)
    session = Session(session_id="token_abc", employee_id=1, tenant_id=1, expires_at=expires)
    await session_repo.save(session)
    await db_session.commit()
    
    # 2. Retrieve Session
    retrieved = await session_repo.find_by_id("token_abc")
    assert retrieved is not None
    assert retrieved.session_id == "token_abc"
    assert retrieved.employee_id == 1
    assert retrieved.tenant_id == 1
    assert retrieved.is_expired() is False
    
    # 3. Invalidate Session
    await session_repo.invalidate("token_abc")
    await db_session.commit()
    
    # 4. Verify invalidation
    invalidated = await session_repo.find_by_id("token_abc")
    assert invalidated is None
