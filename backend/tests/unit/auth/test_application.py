from __future__ import annotations

import datetime

import pytest

from app.auth.application.commands import (
    AssignRoleCommand,
    AssignRoleHandler,
    CreateEmployeeCommand,
    CreateEmployeeHandler,
    LoginCommand,
    LoginHandler,
    LogoutCommand,
    LogoutHandler,
)
from app.auth.application.queries import (
    GetEmployeeHandler,
    GetEmployeeQuery,
    GetSessionHandler,
    GetSessionQuery,
)
from app.auth.domain.employee import Employee, EmployeeRepository, RoleType
from app.auth.domain.session import Session, SessionRepository
from app.auth.domain.tenant import PlanType, Tenant, TenantRepository
from app.shared.exceptions import DomainException
from app.shared.value_objects import Email


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


class InMemoryEmployeeRepository(EmployeeRepository):
    def __init__(self) -> None:
        self._employees: dict[int, Employee] = {}

    async def find_by_id(self, id: int) -> Employee | None:
        return self._employees.get(id)

    async def find_by_email(self, email: Email) -> Employee | None:
        for emp in self._employees.values():
            if str(emp.email) == str(email):
                return emp
        return None

    async def save(self, employee: Employee) -> None:
        self._employees[employee.id] = employee


class InMemorySessionRepository(SessionRepository):
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    async def find_by_id(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    async def save(self, session: Session) -> None:
        self._sessions[session.session_id] = session

    async def invalidate(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)


@pytest.fixture()
def tenant_repo() -> InMemoryTenantRepository:
    return InMemoryTenantRepository()


@pytest.fixture()
def employee_repo() -> InMemoryEmployeeRepository:
    return InMemoryEmployeeRepository()


@pytest.fixture()
def session_repo() -> InMemorySessionRepository:
    return InMemorySessionRepository()


@pytest.mark.unit()
async def test_create_employee_success(employee_repo: InMemoryEmployeeRepository) -> None:
    # Arrange
    handler = CreateEmployeeHandler(employee_repo)
    command = CreateEmployeeCommand(
        id=1, name="John Doe", email="john@comandafacil.com", password="secure_password_123"
    )

    # Act
    employee = await handler.handle(command)

    # Assert
    assert employee.id == 1
    assert employee.name == "John Doe"
    assert str(employee.email) == "john@comandafacil.com"
    assert employee.check_password("secure_password_123") is True

    saved = await employee_repo.find_by_id(1)
    assert saved is not None
    assert saved.name == "John Doe"


@pytest.mark.unit()
async def test_create_employee_duplicate_email(employee_repo: InMemoryEmployeeRepository) -> None:
    # Arrange
    handler = CreateEmployeeHandler(employee_repo)
    existing_emp = Employee.create(1, "Existing", Email("john@comandafacil.com"), "pass")
    await employee_repo.save(existing_emp)

    command = CreateEmployeeCommand(
        id=2, name="John Doe", email="john@comandafacil.com", password="secure_password_123"
    )

    # Act & Assert
    with pytest.raises(DomainException, match="Email already registered"):
        await handler.handle(command)


@pytest.mark.unit()
async def test_assign_role_success(
    employee_repo: InMemoryEmployeeRepository, tenant_repo: InMemoryTenantRepository
) -> None:
    # Arrange
    tenant = Tenant(id=10, name="Main Franchise", plan_type=PlanType.PRO, is_active=True)
    await tenant_repo.save(tenant)

    employee = Employee.create(1, "John Doe", Email("john@comandafacil.com"), "pass")
    await employee_repo.save(employee)

    handler = AssignRoleHandler(employee_repo, tenant_repo)
    command = AssignRoleCommand(employee_id=1, tenant_id=10, role_type=RoleType.MANAGER)

    # Act
    await handler.handle(command)

    # Assert
    saved_emp = await employee_repo.find_by_id(1)
    assert saved_emp is not None
    assert len(saved_emp.roles) == 1
    assert saved_emp.roles[0].tenant_id == 10
    assert saved_emp.roles[0].role_type == RoleType.MANAGER


@pytest.mark.unit()
async def test_assign_role_nonexistent_employee(
    employee_repo: InMemoryEmployeeRepository, tenant_repo: InMemoryTenantRepository
) -> None:
    # Arrange
    tenant = Tenant(id=10, name="Main Franchise", plan_type=PlanType.PRO, is_active=True)
    await tenant_repo.save(tenant)

    handler = AssignRoleHandler(employee_repo, tenant_repo)
    command = AssignRoleCommand(employee_id=99, tenant_id=10, role_type=RoleType.MANAGER)

    # Act & Assert
    with pytest.raises(DomainException, match="Employee not found"):
        await handler.handle(command)


@pytest.mark.unit()
async def test_assign_role_nonexistent_tenant(
    employee_repo: InMemoryEmployeeRepository, tenant_repo: InMemoryTenantRepository
) -> None:
    # Arrange
    employee = Employee.create(1, "John Doe", Email("john@comandafacil.com"), "pass")
    await employee_repo.save(employee)

    handler = AssignRoleHandler(employee_repo, tenant_repo)
    command = AssignRoleCommand(employee_id=1, tenant_id=99, role_type=RoleType.MANAGER)

    # Act & Assert
    with pytest.raises(DomainException, match="Tenant not found"):
        await handler.handle(command)


@pytest.mark.unit()
async def test_login_success(
    employee_repo: InMemoryEmployeeRepository,
    tenant_repo: InMemoryTenantRepository,
    session_repo: InMemorySessionRepository,
) -> None:
    # Arrange
    tenant = Tenant(id=10, name="Main Franchise", plan_type=PlanType.PRO, is_active=True)
    await tenant_repo.save(tenant)

    employee = Employee.create(1, "John Doe", Email("john@comandafacil.com"), "secure_password")
    employee.add_role(tenant, RoleType.WAITER)
    await employee_repo.save(employee)

    handler = LoginHandler(employee_repo, tenant_repo, session_repo)
    command = LoginCommand(email="john@comandafacil.com", password="secure_password", tenant_id=10)

    # Act
    session = await handler.handle(command)

    # Assert
    assert session.employee_id == 1
    assert session.tenant_id == 10
    assert session.is_expired() is False

    saved_session = await session_repo.find_by_id(session.session_id)
    assert saved_session is not None
    assert saved_session.employee_id == 1


@pytest.mark.unit()
async def test_login_invalid_credentials(
    employee_repo: InMemoryEmployeeRepository,
    tenant_repo: InMemoryTenantRepository,
    session_repo: InMemorySessionRepository,
) -> None:
    # Arrange
    handler = LoginHandler(employee_repo, tenant_repo, session_repo)
    command = LoginCommand(email="nonexistent@comandafacil.com", password="any", tenant_id=10)

    # Act & Assert
    with pytest.raises(DomainException, match="Invalid credentials"):
        await handler.handle(command)


@pytest.mark.unit()
async def test_login_incorrect_password(
    employee_repo: InMemoryEmployeeRepository,
    tenant_repo: InMemoryTenantRepository,
    session_repo: InMemorySessionRepository,
) -> None:
    # Arrange
    tenant = Tenant(id=10, name="Main Franchise", plan_type=PlanType.PRO, is_active=True)
    await tenant_repo.save(tenant)

    employee = Employee.create(1, "John Doe", Email("john@comandafacil.com"), "secure_password")
    await employee_repo.save(employee)

    handler = LoginHandler(employee_repo, tenant_repo, session_repo)
    command = LoginCommand(email="john@comandafacil.com", password="wrong_password", tenant_id=10)

    # Act & Assert
    with pytest.raises(DomainException, match="Invalid credentials"):
        await handler.handle(command)


@pytest.mark.unit()
async def test_login_no_role_in_tenant(
    employee_repo: InMemoryEmployeeRepository,
    tenant_repo: InMemoryTenantRepository,
    session_repo: InMemorySessionRepository,
) -> None:
    # Arrange
    tenant = Tenant(id=10, name="Main Franchise", plan_type=PlanType.PRO, is_active=True)
    await tenant_repo.save(tenant)
    other_tenant = Tenant(id=20, name="Other", plan_type=PlanType.PRO, is_active=True)

    employee = Employee.create(1, "John Doe", Email("john@comandafacil.com"), "secure_password")
    # Role in tenant 20, but not 10
    employee.add_role(other_tenant, RoleType.WAITER)
    await employee_repo.save(employee)

    handler = LoginHandler(employee_repo, tenant_repo, session_repo)
    command = LoginCommand(email="john@comandafacil.com", password="secure_password", tenant_id=10)

    # Act & Assert
    with pytest.raises(DomainException, match="No permissions in this tenant"):
        await handler.handle(command)


@pytest.mark.unit()
async def test_login_inactive_tenant(
    employee_repo: InMemoryEmployeeRepository,
    tenant_repo: InMemoryTenantRepository,
    session_repo: InMemorySessionRepository,
) -> None:
    # Arrange
    tenant = Tenant(id=10, name="Main Franchise", plan_type=PlanType.PRO, is_active=False)
    await tenant_repo.save(tenant)

    employee = Employee.create(1, "John Doe", Email("john@comandafacil.com"), "secure_password")
    employee.add_role(tenant, RoleType.WAITER)
    await employee_repo.save(employee)

    handler = LoginHandler(employee_repo, tenant_repo, session_repo)
    command = LoginCommand(email="john@comandafacil.com", password="secure_password", tenant_id=10)

    # Act & Assert
    with pytest.raises(DomainException, match="Tenant is inactive"):
        await handler.handle(command)


@pytest.mark.unit()
async def test_logout_success(session_repo: InMemorySessionRepository) -> None:
    # Arrange
    session = Session(
        session_id="token123",
        employee_id=1,
        tenant_id=10,
        expires_at=datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=1),
    )
    await session_repo.save(session)

    handler = LogoutHandler(session_repo)
    command = LogoutCommand(session_id="token123")

    # Act
    await handler.handle(command)

    # Assert
    assert await session_repo.find_by_id("token123") is None


@pytest.mark.unit()
async def test_get_employee_query(employee_repo: InMemoryEmployeeRepository) -> None:
    # Arrange
    employee = Employee.create(1, "John Doe", Email("john@comandafacil.com"), "pass")
    await employee_repo.save(employee)

    handler = GetEmployeeHandler(employee_repo)
    query = GetEmployeeQuery(email="john@comandafacil.com")

    # Act
    result = await handler.handle(query)

    # Assert
    assert result is not None
    assert result.id == 1
    assert result.name == "John Doe"


@pytest.mark.unit()
async def test_get_session_query(session_repo: InMemorySessionRepository) -> None:
    # Arrange
    session = Session(
        session_id="token123",
        employee_id=1,
        tenant_id=10,
        expires_at=datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=1),
    )
    await session_repo.save(session)

    handler = GetSessionHandler(session_repo)
    query = GetSessionQuery(session_id="token123")

    # Act
    result = await handler.handle(query)

    # Assert
    assert result is not None
    assert result.employee_id == 1
    assert result.tenant_id == 10
