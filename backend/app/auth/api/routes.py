from __future__ import annotations

import datetime
from typing import Final
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, EmailStr, Field, ConfigDict

from app.auth.domain.employee import RoleType
from app.auth.infrastructure.repositories import (
    SQLAlchemyEmployeeRepository,
    SQLAlchemyTenantRepository,
    SQLAlchemySessionRepository,
)
from app.dependencies import DbSession, CurrentEmployee, CurrentSession
from app.auth.application.commands import (
    CreateEmployeeCommand,
    CreateEmployeeHandler,
    AssignRoleCommand,
    AssignRoleHandler,
    LoginCommand,
    LoginHandler,
    LogoutCommand,
    LogoutHandler,
)
from app.auth.application.queries import (
    GetEmployeeQuery,
    GetEmployeeHandler,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


# ─── Pydantic Schemas ─────────────────────────────────────────────────────────

class EmployeeRegisterSchema(BaseModel):
    """Schema for registering a new Employee."""
    id: int = Field(..., description="Unique employee identifier")
    name: str = Field(..., max_length=255, description="Full name of the employee")
    email: EmailStr = Field(..., description="Validated corporate email address")
    password: str = Field(..., min_length=6, description="Plaintext password, min 6 characters")

    model_config = ConfigDict(frozen=True)


class EmployeeResponseSchema(BaseModel):
    """Schema for returning Employee information."""
    id: int
    name: str
    email: str

    model_config = ConfigDict(from_attributes=True, frozen=True)


class AssignRoleSchema(BaseModel):
    """Schema for assigning a role to an Employee."""
    tenant_id: int = Field(..., description="Tenant franchise ID")
    role_type: RoleType = Field(..., description="Role type (e.g. MANAGER, WAITER, COOK, CASHIER)")

    model_config = ConfigDict(frozen=True)


class LoginSchema(BaseModel):
    """Schema for logging in."""
    email: EmailStr = Field(..., description="Employee corporate email")
    password: str = Field(..., description="Plaintext password")
    tenant_id: int = Field(..., description="Target tenant franchise ID to login into")

    model_config = ConfigDict(frozen=True)


class SessionResponseSchema(BaseModel):
    """Schema returning session details after successful login."""
    session_id: str = Field(..., description="Bearer session token identifier")
    expires_at: datetime.datetime = Field(..., description="Session expiration timestamp")

    model_config = ConfigDict(from_attributes=True, frozen=True)


# ─── REST Endpoints ───────────────────────────────────────────────────────────

@router.post(
    "/employees",
    response_model=EmployeeResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new Employee"
)
async def register_employee(
    schema: EmployeeRegisterSchema,
    db: DbSession
) -> EmployeeResponseSchema:
    """Registers a new employee aggregate in the global system."""
    repo = SQLAlchemyEmployeeRepository(db)
    handler = CreateEmployeeHandler(repo)
    command = CreateEmployeeCommand(
        id=schema.id,
        name=schema.name,
        email=str(schema.email),
        password=schema.password
    )
    employee = await handler.handle(command)
    await db.commit()
    return EmployeeResponseSchema(
        id=employee.id,
        name=employee.name,
        email=str(employee.email)
    )


@router.post(
    "/employees/{employee_id}/roles",
    status_code=status.HTTP_200_OK,
    summary="Assign franchise role to Employee"
)
async def assign_role(
    employee_id: int,
    schema: AssignRoleSchema,
    db: DbSession
) -> dict[str, str]:
    """Assigns a role to an employee within a specific tenant franchise."""
    emp_repo = SQLAlchemyEmployeeRepository(db)
    tenant_repo = SQLAlchemyTenantRepository(db)
    handler = AssignRoleHandler(emp_repo, tenant_repo)
    command = AssignRoleCommand(
        employee_id=employee_id,
        tenant_id=schema.tenant_id,
        role_type=schema.role_type
    )
    await handler.handle(command)
    await db.commit()
    return {"detail": "Role assigned successfully"}


@router.post(
    "/login",
    response_model=SessionResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Employee Franchise Login"
)
async def login(
    schema: LoginSchema,
    db: DbSession
) -> SessionResponseSchema:
    """Authenticates credentials, checks franchise access, and establishes a stateful Session."""
    emp_repo = SQLAlchemyEmployeeRepository(db)
    tenant_repo = SQLAlchemyTenantRepository(db)
    session_repo = SQLAlchemySessionRepository(db)
    handler = LoginHandler(emp_repo, tenant_repo, session_repo)
    command = LoginCommand(
        email=str(schema.email),
        password=schema.password,
        tenant_id=schema.tenant_id
    )
    session = await handler.handle(command)
    await db.commit()
    return SessionResponseSchema(
        session_id=session.session_id,
        expires_at=session.expires_at
    )


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Employee Session Logout"
)
async def logout(
    current_session: CurrentSession,
    db: DbSession
) -> dict[str, str]:
    """Invalidates and deletes the active stateful session."""
    session_repo = SQLAlchemySessionRepository(db)
    handler = LogoutHandler(session_repo)
    command = LogoutCommand(session_id=current_session.session_id)
    await handler.handle(command)
    await db.commit()
    return {"detail": "Logged out successfully"}


@router.get(
    "/me",
    response_model=EmployeeResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Get authenticated Employee profile"
)
async def get_me(
    current_employee: CurrentEmployee
) -> EmployeeResponseSchema:
    """Returns the profile of the currently logged-in employee."""
    return EmployeeResponseSchema(
        id=current_employee.id,
        name=current_employee.name,
        email=str(current_employee.email)
    )
