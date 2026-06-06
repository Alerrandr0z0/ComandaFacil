from __future__ import annotations

import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

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
from app.auth.domain.employee import RoleType
from app.auth.infrastructure.orm_models import EmployeeORM
from app.auth.infrastructure.repositories import (
    SQLAlchemyEmployeeRepository,
    SQLAlchemySessionRepository,
    SQLAlchemyTenantRepository,
)
from app.dependencies import (
    CurrentEmployee,
    CurrentSession,
    DbSession,
    get_current_tenant_id,
    require_permission,
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
    role: str | None = None
    is_active: bool = True

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


@router.get(
    "/employees",
    response_model=list[EmployeeResponseSchema],
    status_code=status.HTTP_200_OK,
    summary="Get all employees in the current tenant franchise",
)
async def list_employees(
    db: DbSession,
    tenant_id: str = Depends(get_current_tenant_id),
) -> list[EmployeeResponseSchema]:
    """Lists all registered employees and resolves their active role for the tenant."""
    stmt = select(EmployeeORM).options(selectinload(EmployeeORM.roles))
    result = await db.execute(stmt)
    orms = result.scalars().all()

    response = []
    try:
        t_id = int(tenant_id)
    except ValueError:
        t_id = None

    for orm in orms:
        active_role = None
        is_active = True
        if t_id is not None:
            for r in orm.roles:
                if r.tenant_id == t_id:
                    active_role = r.role_type
                    is_active = r.is_active
                    break
        response.append(
            EmployeeResponseSchema(
                id=orm.id,
                name=orm.name,
                email=orm.email,
                role=active_role,
                is_active=is_active,
            )
        )
    return response


@router.post(
    "/employees",
    response_model=EmployeeResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new Employee",
)
async def register_employee(
    schema: EmployeeRegisterSchema, db: DbSession
) -> EmployeeResponseSchema:
    """Registers a new employee aggregate in the global system."""
    repo = SQLAlchemyEmployeeRepository(db)
    handler = CreateEmployeeHandler(repo)
    command = CreateEmployeeCommand(
        id=schema.id, name=schema.name, email=str(schema.email), password=schema.password
    )
    employee = await handler.handle(command)
    await db.commit()
    return EmployeeResponseSchema(id=employee.id, name=employee.name, email=str(employee.email))


@router.post(
    "/employees/{employee_id}/roles",
    status_code=status.HTTP_200_OK,
    summary="Assign franchise role to Employee",
)
async def assign_role(employee_id: int, schema: AssignRoleSchema, db: DbSession) -> dict[str, str]:
    """Assigns a role to an employee within a specific tenant franchise."""
    emp_repo = SQLAlchemyEmployeeRepository(db)
    tenant_repo = SQLAlchemyTenantRepository(db)
    handler = AssignRoleHandler(emp_repo, tenant_repo)
    command = AssignRoleCommand(
        employee_id=employee_id, tenant_id=schema.tenant_id, role_type=schema.role_type
    )
    await handler.handle(command)
    await db.commit()
    return {"detail": "Role assigned successfully"}


@router.post(
    "/login",
    response_model=SessionResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Employee Franchise Login",
)
async def login(schema: LoginSchema, db: DbSession) -> SessionResponseSchema:
    """Authenticates credentials, checks franchise access, and establishes a stateful Session."""
    emp_repo = SQLAlchemyEmployeeRepository(db)
    tenant_repo = SQLAlchemyTenantRepository(db)
    session_repo = SQLAlchemySessionRepository(db)
    handler = LoginHandler(emp_repo, tenant_repo, session_repo)
    command = LoginCommand(
        email=str(schema.email), password=schema.password, tenant_id=schema.tenant_id
    )
    session = await handler.handle(command)
    await db.commit()
    return SessionResponseSchema(session_id=session.session_id, expires_at=session.expires_at)


@router.post("/logout", status_code=status.HTTP_200_OK, summary="Employee Session Logout")
async def logout(current_session: CurrentSession, db: DbSession) -> dict[str, str]:
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
    summary="Get authenticated Employee profile",
)
async def get_me(
    current_employee: CurrentEmployee,
    tenant_id: str = Depends(get_current_tenant_id),
) -> EmployeeResponseSchema:
    """Returns the profile of the currently logged-in employee."""
    active_role = None
    try:
        t_id = int(tenant_id)
        for role in current_employee.roles:
            if role.tenant_id == t_id and role.is_active:
                active_role = role.role_type.value
                break
    except ValueError:
        pass

    return EmployeeResponseSchema(
        id=current_employee.id,
        name=current_employee.name,
        email=str(current_employee.email),
        role=active_role,
    )


@router.post(
    "/employees/{employee_id}/toggle-active",
    status_code=status.HTTP_200_OK,
    summary="Toggle active status of a franchise employee",
    dependencies=[Depends(require_permission("MANAGE_EMPLOYEES"))],
)
async def toggle_active_employee(
    employee_id: int,
    db: DbSession,
    tenant_id_str: str = Depends(get_current_tenant_id),
) -> dict[str, bool]:
    try:
        t_id = int(tenant_id_str)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid tenant ID format.",
        ) from err

    emp_repo = SQLAlchemyEmployeeRepository(db)
    tenant_repo = SQLAlchemyTenantRepository(db)
    employee = await emp_repo.find_by_id(employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Colaborador não encontrado.")

    tenant = await tenant_repo.find_by_id(t_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Franquia não encontrada.")

    role = next((r for r in employee.roles if r.tenant_id == t_id), None)
    if not role:
        raise HTTPException(status_code=400, detail="Colaborador não possui cargo associado a esta franquia.")

    # Toggle active status
    if role.is_active:
        role.deactivate()
    else:
        role.is_active = True

    await emp_repo.save(employee)
    await db.commit()
    return {"is_active": role.is_active}


@router.delete(
    "/employees/{employee_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove an employee from the franchise",
    dependencies=[Depends(require_permission("MANAGE_EMPLOYEES"))],
)
async def delete_employee(
    employee_id: int,
    db: DbSession,
    tenant_id_str: str = Depends(get_current_tenant_id),
) -> dict[str, str]:
    try:
        t_id = int(tenant_id_str)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid tenant ID format.",
        ) from err

    emp_repo = SQLAlchemyEmployeeRepository(db)
    tenant_repo = SQLAlchemyTenantRepository(db)
    employee = await emp_repo.find_by_id(employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Colaborador não encontrado.")

    tenant = await tenant_repo.find_by_id(t_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Franquia não encontrada.")

    try:
        employee.remove_role(tenant)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    await emp_repo.save(employee)
    await db.commit()
    return {"detail": "Colaborador removido da franquia com sucesso."}
