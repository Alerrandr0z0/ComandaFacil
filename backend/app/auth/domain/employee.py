from __future__ import annotations

import datetime
import hashlib
import secrets
from abc import ABC, abstractmethod
from enum import StrEnum
from typing import TYPE_CHECKING, Final

from app.shared.exceptions import DomainException

if TYPE_CHECKING:
    from app.auth.domain.tenant import Tenant
    from app.shared.value_objects import Email


class RoleType(StrEnum):
    MANAGER = "MANAGER"
    WAITER = "WAITER"
    COOK = "COOK"
    CASHIER = "CASHIER"
    SUPER_ADMIN = "SUPER_ADMIN"


class IEmployeeStrategy(ABC):
    """Abstract behavioral strategy interface for defining employee permissions."""

    @abstractmethod
    def permits(self, action: str) -> bool:
        """Determines if a specific action is permitted under this strategy."""


class ManagerStrategy(IEmployeeStrategy):
    """Strategy granting full permissions for managers."""

    def permits(self, action: str) -> bool:  # noqa: ARG002
        return True


class WaiterStrategy(IEmployeeStrategy):
    """Strategy defining waiter specific permissions."""

    def permits(self, action: str) -> bool:
        return action == "CREATE_ORDER"


class CookStrategy(IEmployeeStrategy):
    """Strategy defining cook specific permissions."""

    def permits(self, action: str) -> bool:
        return action == "PREPARE_ITEM"


class CashierStrategy(IEmployeeStrategy):
    """Strategy defining cashier specific permissions."""

    def permits(self, action: str) -> bool:
        return action == "CLOSE_ORDER"


class AdminStrategy(IEmployeeStrategy):
    """Strategy granting full permissions for super admins."""

    def permits(self, action: str) -> bool:  # noqa: ARG002
        return True


class RolePermissions:
    """Factory mapping employee role types to their concrete permission strategies."""

    @staticmethod
    def resolver(role_type: RoleType | str) -> IEmployeeStrategy:
        """Resolves the concrete strategy associated with a specific role type."""
        if not isinstance(role_type, RoleType):
            try:
                role_type = RoleType(role_type)
            except ValueError as err:
                raise ValueError(f"Cargo inválido: {role_type}") from err

        match role_type:
            case RoleType.MANAGER:
                return ManagerStrategy()
            case RoleType.WAITER:
                return WaiterStrategy()
            case RoleType.COOK:
                return CookStrategy()
            case RoleType.CASHIER:
                return CashierStrategy()
            case RoleType.SUPER_ADMIN:
                return AdminStrategy()
            case _:
                raise ValueError(f"Cargo sem estratégia definida: {role_type}")


class UserTenantRole:
    """
    Entity mapping an employee to a specific tenant with a specific role.

    Attributes:
        id: Unique identifier of the role mapping.
        tenant_id: Reference ID of the tenant franchise.
        employee_id: Reference ID of the employee.
        role_type: Role assigned to the employee.
        is_active: Active status of the mapping.
        assigned_at: Timestamp indicating when the role was assigned.
    """

    def __init__(
        self, id: int, tenant_id: int, employee_id: int, role_type: RoleType, is_active: bool = True
    ) -> None:
        self.id: Final[int] = id
        self.tenant_id: Final[int] = tenant_id
        self.employee_id: Final[int] = employee_id
        self.role_type: RoleType = role_type
        self.is_active: bool = is_active
        self.assigned_at: Final[datetime.datetime] = datetime.datetime.now(datetime.UTC)

    def is_expired(self) -> bool:
        """Checks if the role assignment is currently suspended or inactive."""
        return not self.is_active

    def deactivate(self) -> None:
        """Deactivates/suspends the role assignment."""
        self.is_active = False

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self.id}, tenant_id={self.tenant_id}, employee_id={self.employee_id}, role_type={self.role_type!r}, is_active={self.is_active})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, UserTenantRole):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)


class Employee:
    """
    Employee (Aggregate Root) representing a restaurant employee.
    Manages their own passwords, tenant roles, and acts as the entry point
    for permission checking.

    Attributes:
        id: Unique identifier of the employee.
        name: Complete name of the employee.
        email: Validated Email value object.
        password_hash: Hash representation of the employee password.
        roles: List of franchise role assignments mapping.
    """

    def __init__(self, id: int, name: str, email: Email, password_hash: str) -> None:
        self.id: Final[int] = id
        self.name: str = name
        self.email: Email = email
        self.password_hash: str = password_hash
        self.roles: list[UserTenantRole] = []

    @classmethod
    def create(cls, id: int, name: str, email: Email, password: str) -> Employee:
        """Factory method to create a new Employee aggregate with a hashed password."""
        employee = cls(id=id, name=name, email=email, password_hash="")
        employee.set_password(password)
        return employee

    def set_password(self, password: str) -> None:
        """Hashes and sets the password for the employee using PBKDF2-SHA256."""
        salt = secrets.token_hex(16)
        key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
        self.password_hash = f"pbkdf2_sha256$100000${salt}${key.hex()}"

    def check_password(self, password: str) -> bool:
        """Verifies if the provided plain text password matches the employee hash."""
        hashed = self.password_hash
        if not hashed or not hashed.startswith("pbkdf2_sha256$"):
            return False
        try:
            parts = hashed.split("$")
            pbkdf2_parts_count = 4
            if len(parts) != pbkdf2_parts_count:
                return False
            _, iterations_str, salt, original_key_hex = parts
            iterations = int(iterations_str)
            key = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations
            )
            return secrets.compare_digest(key.hex(), original_key_hex)
        except Exception:
            return False

    def add_role(self, tenant: Tenant, role_type: RoleType) -> None:
        """Assigns a new role for a specific franchise/tenant."""
        for role in self.roles:
            if role.tenant_id == tenant.id:
                raise DomainException("Funcionário já possui cargo associado a esta franquia.")

        new_role = UserTenantRole(
            id=len(self.roles) + 1,
            tenant_id=tenant.id,
            employee_id=self.id,
            role_type=role_type,
            is_active=True,
        )
        self.roles.append(new_role)

    def get_role_for_tenant(self, tenant: Tenant) -> UserTenantRole:
        """Fetches the active role mapping for a specific franchise/tenant."""
        for role in self.roles:
            if role.tenant_id == tenant.id and role.is_active:
                return role
        raise DomainException("Funcionário não possui cargo ativo nesta franquia.")

    def remove_role(self, tenant: Tenant) -> None:
        """Removes the role assignment mapping associated with a specific tenant."""
        for i, role in enumerate(self.roles):
            if role.tenant_id == tenant.id:
                self.roles.pop(i)
                return
        raise DomainException("Cargo não encontrado para esta franquia.")

    def permits(self, action: str, tenant: Tenant) -> bool:
        """
        Pure OOP delegation: the aggregate root verifies permissions by delegating
        to the resolved behavioral strategy.
        """
        try:
            role = self.get_role_for_tenant(tenant)
            strategy = RolePermissions.resolver(role.role_type)
            return strategy.permits(action)
        except DomainException:
            return False

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self.id}, name={self.name!r}, email={self.email!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Employee):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)


class EmployeeRepository(ABC):
    """Abstract Repository Interface for Employee Aggregate Root."""

    @abstractmethod
    async def find_by_id(self, id: int) -> Employee | None:
        """Retrieves an Employee by their unique identifier."""

    @abstractmethod
    async def find_by_email(self, email: Email) -> Employee | None:
        """Retrieves an Employee by their validated Email."""

    @abstractmethod
    async def save(self, employee: Employee) -> None:
        """Saves or updates an Employee in persistent storage."""
