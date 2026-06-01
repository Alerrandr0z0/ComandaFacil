from __future__ import annotations

import datetime
from sqlalchemy import ForeignKey, String, Boolean, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.auth.domain.tenant import PlanType
from app.shared.base_orm import Base


class TenantORM(Base):
    """SQLAlchemy model for tenants table."""
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    plan_type: Mapped[str] = mapped_column(String(50), default=PlanType.BASIC.value)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    roles: Mapped[list[UserTenantRoleORM]] = relationship(
        "UserTenantRoleORM", back_populates="tenant", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"TenantORM(id={self.id}, name={self.name!r}, plan_type={self.plan_type!r}, is_active={self.is_active})"


class EmployeeORM(Base):
    """SQLAlchemy model for employees table."""
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Relationships
    roles: Mapped[list[UserTenantRoleORM]] = relationship(
        "UserTenantRoleORM", back_populates="employee", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"EmployeeORM(id={self.id}, name={self.name!r}, email={self.email!r})"


class UserTenantRoleORM(Base):
    """SQLAlchemy model for user_tenant_roles table."""
    __tablename__ = "user_tenant_roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    role_type: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    assigned_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    # Relationships
    tenant: Mapped[TenantORM] = relationship("TenantORM", back_populates="roles")
    employee: Mapped[EmployeeORM] = relationship("EmployeeORM", back_populates="roles")

    def __repr__(self) -> str:
        return f"UserTenantRoleORM(id={self.id}, tenant_id={self.tenant_id}, employee_id={self.employee_id}, role_type={self.role_type!r}, is_active={self.is_active})"


class SessionORM(Base):
    """SQLAlchemy model for sessions table."""
    __tablename__ = "sessions"

    session_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def __repr__(self) -> str:
        return f"SessionORM(session_id={self.session_id!r}, employee_id={self.employee_id}, tenant_id={self.tenant_id}, expires_at={self.expires_at!r})"
