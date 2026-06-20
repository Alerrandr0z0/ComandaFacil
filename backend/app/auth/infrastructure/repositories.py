from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.auth.domain.employee import Employee, EmployeeRepository, RoleType, UserTenantRole
from app.auth.domain.session import Session, SessionRepository
from app.auth.domain.tenant import PlanType, Tenant, TenantRepository
from app.auth.infrastructure.orm_models import EmployeeORM, SessionORM, TenantORM, UserTenantRoleORM
from app.shared.value_objects import Email

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class SQLAlchemyTenantRepository(TenantRepository):
    """SQLAlchemy implementation of TenantRepository interface."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_id(self, id: int) -> Tenant | None:
        stmt = select(TenantORM).where(TenantORM.id == id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if not orm:
            return None
        return Tenant(
            id=orm.id, name=orm.name, plan_type=PlanType(orm.plan_type), is_active=orm.is_active
        )

    async def save(self, tenant: Tenant) -> None:
        stmt = select(TenantORM).where(TenantORM.id == tenant.id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm:
            orm.name = tenant.name
            orm.plan_type = tenant.plan_type.value
            orm.is_active = tenant.is_active
        else:
            orm = TenantORM(
                id=tenant.id,
                name=tenant.name,
                plan_type=tenant.plan_type.value,
                is_active=tenant.is_active,
            )
            self._session.add(orm)
        await self._session.flush()

    async def find_all(self) -> list[Tenant]:
        stmt = select(TenantORM)
        result = await self._session.execute(stmt)
        orms = result.scalars().all()
        return [
            Tenant(
                id=orm.id, name=orm.name, plan_type=PlanType(orm.plan_type), is_active=orm.is_active
            )
            for orm in orms
        ]

    async def delete(self, id: int) -> None:
        stmt = delete(TenantORM).where(TenantORM.id == id)
        await self._session.execute(stmt)
        await self._session.flush()


class SQLAlchemyEmployeeRepository(EmployeeRepository):
    """SQLAlchemy implementation of EmployeeRepository interface."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_id(self, id: int) -> Employee | None:
        stmt = (
            select(EmployeeORM).where(EmployeeORM.id == id).options(selectinload(EmployeeORM.roles))
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if not orm:
            return None
        return self._map_to_domain(orm)

    async def find_by_email(self, email: Email) -> Employee | None:
        stmt = (
            select(EmployeeORM)
            .where(EmployeeORM.email == str(email))
            .options(selectinload(EmployeeORM.roles))
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if not orm:
            return None
        return self._map_to_domain(orm)

    async def save(self, employee: Employee) -> None:
        stmt = (
            select(EmployeeORM)
            .where(EmployeeORM.id == employee.id)
            .options(selectinload(EmployeeORM.roles))
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm:
            orm.name = employee.name
            orm.email = str(employee.email)
            orm.password_hash = employee.password_hash
            # Sync roles list
            # Simple approach: clear existing and re-add for simplicity in this domain boundaries
            orm.roles.clear()
        else:
            orm = EmployeeORM(
                id=employee.id,
                name=employee.name,
                email=str(employee.email),
                password_hash=employee.password_hash,
            )
            self._session.add(orm)

        # Add roles ORM mappings
        for role in employee.roles:
            role_orm = UserTenantRoleORM(
                tenant_id=role.tenant_id,
                employee_id=employee.id,
                role_type=role.role_type.value,
                is_active=role.is_active,
            )
            orm.roles.append(role_orm)

        await self._session.flush()

    def _map_to_domain(self, orm: EmployeeORM) -> Employee:
        employee = Employee(
            id=orm.id, name=orm.name, email=Email(orm.email), password_hash=orm.password_hash
        )
        # Map roles list
        for r_orm in orm.roles:
            role = UserTenantRole(
                id=r_orm.id,
                tenant_id=r_orm.tenant_id,
                employee_id=r_orm.employee_id,
                role_type=RoleType(r_orm.role_type),
                is_active=r_orm.is_active,
            )
            # Use private list extension or standard append since aggregate handles it
            employee.roles.append(role)
        return employee


class SQLAlchemySessionRepository(SessionRepository):
    """SQLAlchemy implementation of SessionRepository interface."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_id(self, session_id: str) -> Session | None:
        stmt = select(SessionORM).where(SessionORM.session_id == session_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if not orm:
            return None
        return Session(
            session_id=orm.session_id,
            employee_id=orm.employee_id,
            tenant_id=orm.tenant_id,
            expires_at=orm.expires_at,
        )

    async def save(self, session: Session) -> None:
        stmt = select(SessionORM).where(SessionORM.session_id == session.session_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm:
            orm.employee_id = session.employee_id
            orm.tenant_id = session.tenant_id
            orm.expires_at = session.expires_at
        else:
            orm = SessionORM(
                session_id=session.session_id,
                employee_id=session.employee_id,
                tenant_id=session.tenant_id,
                expires_at=session.expires_at,
            )
            self._session.add(orm)
        await self._session.flush()

    async def invalidate(self, session_id: str) -> None:
        stmt = delete(SessionORM).where(SessionORM.session_id == session_id)
        await self._session.execute(stmt)
        await self._session.flush()
