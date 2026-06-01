from __future__ import annotations

from dataclasses import dataclass
import datetime
import secrets
from typing import Final

from app.auth.domain.employee import Employee, EmployeeRepository, RoleType
from app.auth.domain.tenant import TenantRepository
from app.auth.domain.session import Session, SessionRepository
from app.shared.value_objects import Email
from app.shared.exceptions import DomainException


@dataclass(frozen=True)
class CreateEmployeeCommand:
    """Command data to create a new Employee."""
    id: int
    name: str
    email: str
    password: str

    def __repr__(self) -> str:
        return f"CreateEmployeeCommand(id={self.id}, name={self.name!r}, email={self.email!r})"


class CreateEmployeeHandler:
    """Handler to execute the CreateEmployee use case."""

    def __init__(self, employee_repo: EmployeeRepository) -> None:
        self._employee_repo: Final[EmployeeRepository] = employee_repo

    async def handle(self, command: CreateEmployeeCommand) -> Employee:
        """Creates and persists a new Employee in the system."""
        email_vo = Email(command.email)
        existing = await self._employee_repo.find_by_email(email_vo)
        if existing:
            raise DomainException("Email already registered", status_code=409)

        employee = Employee.create(
            id=command.id,
            name=command.name,
            email=email_vo,
            password=command.password
        )
        await self._employee_repo.save(employee)
        return employee

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"


@dataclass(frozen=True)
class AssignRoleCommand:
    """Command data to assign a role to an Employee within a Tenant franchise."""
    employee_id: int
    tenant_id: int
    role_type: RoleType

    def __repr__(self) -> str:
        return f"AssignRoleCommand(employee_id={self.employee_id}, tenant_id={self.tenant_id}, role_type={self.role_type!r})"


class AssignRoleHandler:
    """Handler to execute the AssignRole use case."""

    def __init__(self, employee_repo: EmployeeRepository, tenant_repo: TenantRepository) -> None:
        self._employee_repo: Final[EmployeeRepository] = employee_repo
        self._tenant_repo: Final[TenantRepository] = tenant_repo

    async def handle(self, command: AssignRoleCommand) -> None:
        """Assigns a specific role to an existing Employee in a validated Tenant."""
        employee = await self._employee_repo.find_by_id(command.employee_id)
        if not employee:
            raise DomainException("Employee not found", status_code=404)

        tenant = await self._tenant_repo.find_by_id(command.tenant_id)
        if not tenant:
            raise DomainException("Tenant not found", status_code=404)

        employee.add_role(tenant, command.role_type)
        await self._employee_repo.save(employee)

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"


@dataclass(frozen=True)
class LoginCommand:
    """Command data to perform user login."""
    email: str
    password: str
    tenant_id: int

    def __repr__(self) -> str:
        return f"LoginCommand(email={self.email!r}, tenant_id={self.tenant_id})"


class LoginHandler:
    """Handler to execute the Login use case."""

    def __init__(
        self,
        employee_repo: EmployeeRepository,
        tenant_repo: TenantRepository,
        session_repo: SessionRepository
    ) -> None:
        self._employee_repo: Final[EmployeeRepository] = employee_repo
        self._tenant_repo: Final[TenantRepository] = tenant_repo
        self._session_repo: Final[SessionRepository] = session_repo

    async def handle(self, command: LoginCommand) -> Session:
        """Validates credentials, checks active role in Tenant, and issues a stateful Session."""
        email_vo = Email(command.email)
        employee = await self._employee_repo.find_by_email(email_vo)
        if not employee or not employee.check_password(command.password):
            raise DomainException("Invalid credentials", status_code=401)

        tenant = await self._tenant_repo.find_by_id(command.tenant_id)
        if not tenant:
            raise DomainException("Tenant not found", status_code=404)

        if not tenant.is_active_tenant():
            raise DomainException("Tenant is inactive", status_code=403)

        # Check if employee has an active role in this tenant
        try:
            employee.get_role_for_tenant(tenant)
        except DomainException:
            raise DomainException("No permissions in this tenant", status_code=403)

        # Generate stateful session
        session_id = secrets.token_urlsafe(32)
        expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=60)
        session = Session(
            session_id=session_id,
            employee_id=employee.id,
            tenant_id=tenant.id,
            expires_at=expires_at
        )

        await self._session_repo.save(session)
        return session

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"


@dataclass(frozen=True)
class LogoutCommand:
    """Command data to perform user logout."""
    session_id: str

    def __repr__(self) -> str:
        return f"LogoutCommand(session_id={self.session_id!r})"


class LogoutHandler:
    """Handler to execute the Logout use case."""

    def __init__(self, session_repo: SessionRepository) -> None:
        self._session_repo: Final[SessionRepository] = session_repo

    async def handle(self, command: LogoutCommand) -> None:
        """Invalidates and deletes a stateful Session by ID."""
        await self._session_repo.invalidate(command.session_id)

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"
