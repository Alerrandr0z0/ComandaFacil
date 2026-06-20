from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Final


class PlanType(StrEnum):
    BASIC = "BASIC"
    PRO = "PRO"
    PLUS = "PLUS"


class Tenant:
    """
    Tenant (Aggregate Root) representing a franchise in the multi-tenant system.

    Attributes:
        id: Unique identifier of the tenant.
        name: Name of the franchise.
        plan_type: Active SaaS plan subscription level.
        is_active: Status indicating if the tenant is active.
    """

    def __init__(self, id: int, name: str, plan_type: PlanType, is_active: bool = True) -> None:
        self.id: Final[int] = id
        self.name: str = name
        self.plan_type: PlanType = plan_type
        self.is_active: bool = is_active

    def is_active_tenant(self) -> bool:
        """Checks if the tenant is active and permitted to operate."""
        return self.is_active

    def activate(self) -> None:
        """Activates the tenant, allowing operations."""
        self.is_active = True

    def deactivate(self) -> None:
        """Deactivates the tenant, suspending operations."""
        self.is_active = False

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self.id}, name={self.name!r}, plan_type={self.plan_type!r}, is_active={self.is_active})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Tenant):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)


class TenantRepository(ABC):
    """Abstract Repository Interface for Tenant Aggregate Root."""

    @abstractmethod
    async def find_by_id(self, id: int) -> Tenant | None:
        """Retrieves a Tenant by its unique identifier."""

    @abstractmethod
    async def find_all(self) -> list[Tenant]:
        """Retrieves all tenants."""

    @abstractmethod
    async def delete(self, id: int) -> None:
        """Deletes a tenant."""

    @abstractmethod
    async def save(self, tenant: Tenant) -> None:
        """Saves or updates a Tenant in persistent storage."""
