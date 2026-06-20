import csv
import io
import logging
from typing import Any

from fastapi import APIRouter, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.admin.application.commands import (
    CreateTenantCommand,
    DeleteTenantCommand,
    handle_create_tenant,
    handle_delete_tenant,
)
from app.admin.application.queries import (
    GetGlobalAnalyticsQuery,
    GetTenantsQuery,
    handle_get_global_analytics,
    handle_get_tenants,
)
from app.auth.domain.employee import Employee, RoleType
from app.auth.domain.tenant import PlanType, Tenant
from app.auth.infrastructure.orm_models import EmployeeORM, UserTenantRoleORM
from app.auth.infrastructure.repositories import (
    SQLAlchemyEmployeeRepository,
    SQLAlchemyTenantRepository,
)
from app.dependencies import CurrentAdminEmployee, DbSession, MongoDB
from app.shared.exceptions import DomainException
from app.shared.value_objects import Email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


class TenantResponseSchema(BaseModel):
    id: int
    name: str
    plan_type: PlanType
    is_active: bool

    model_config = ConfigDict(from_attributes=True, frozen=True)


class ManagerResponseSchema(BaseModel):
    id: int
    name: str
    email: str
    tenant_id: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True, frozen=True)


class CreateManagerSchema(BaseModel):
    name: str
    email: str
    password: str
    tenant_id: int

    model_config = ConfigDict(frozen=True)


@router.post("/tenants", response_model=TenantResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    command: CreateTenantCommand,
    db: DbSession,
    _: CurrentAdminEmployee,
) -> Tenant:
    repo = SQLAlchemyTenantRepository(db)
    tenant = await handle_create_tenant(command, repo)
    await db.commit()
    return tenant


@router.get("/tenants", response_model=list[TenantResponseSchema], status_code=status.HTTP_200_OK)
async def get_tenants(
    db: DbSession,
    _: CurrentAdminEmployee,
) -> list[Tenant]:
    repo = SQLAlchemyTenantRepository(db)
    query = GetTenantsQuery()
    return await handle_get_tenants(query, repo)


@router.delete("/tenants/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: int,
    db: DbSession,
    _: CurrentAdminEmployee,
) -> None:
    repo = SQLAlchemyTenantRepository(db)
    command = DeleteTenantCommand(tenant_id=tenant_id)
    await handle_delete_tenant(command, repo)
    await db.commit()


@router.get("/managers", response_model=list[ManagerResponseSchema], status_code=status.HTTP_200_OK)
async def get_managers(
    db: DbSession,
    _: CurrentAdminEmployee,
) -> list[dict[str, Any]]:
    # Select employees who have role 'MANAGER'
    stmt = (
        select(EmployeeORM)
        .join(EmployeeORM.roles)
        .where(UserTenantRoleORM.role_type == "MANAGER")
        .options(selectinload(EmployeeORM.roles))
    )
    result = await db.execute(stmt)
    orms = result.scalars().unique().all()

    managers = []
    for orm in orms:
        manager_role = next((r for r in orm.roles if r.role_type == "MANAGER"), None)
        if manager_role:
            managers.append(
                {
                    "id": orm.id,
                    "name": orm.name,
                    "email": orm.email,
                    "tenant_id": manager_role.tenant_id,
                    "is_active": manager_role.is_active,
                }
            )
    return managers


@router.post("/managers", response_model=ManagerResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_manager(
    schema: CreateManagerSchema,
    db: DbSession,
    _: CurrentAdminEmployee,
) -> dict[str, Any]:
    email_vo = Email(schema.email)

    # Check if email is already taken
    stmt = select(EmployeeORM).where(EmployeeORM.email == str(email_vo))
    res = await db.execute(stmt)
    existing_orm = res.scalar_one_or_none()

    emp_repo = SQLAlchemyEmployeeRepository(db)
    tenant_repo = SQLAlchemyTenantRepository(db)

    tenant = await tenant_repo.find_by_id(schema.tenant_id)
    if not tenant:
        raise DomainException("Tenant not found", status_code=404)

    if existing_orm:
        employee = await emp_repo.find_by_id(existing_orm.id)
        if not employee:
            raise DomainException("Employee not found", status_code=404)

        # Check if they already have MANAGER role in this tenant
        has_manager = any(
            r.tenant_id == schema.tenant_id and r.role_type == RoleType.MANAGER
            for r in employee.roles
        )
        if has_manager:
            raise DomainException("Employee is already a manager of this tenant", status_code=409)
    else:
        # Generate new ID
        stmt_max = select(func.max(EmployeeORM.id))
        res_max = await db.execute(stmt_max)
        max_id = res_max.scalar() or 0
        new_id = max_id + 1

        employee = Employee.create(
            id=new_id,
            name=schema.name,
            email=email_vo,
            password=schema.password,
        )

    employee.add_role(tenant, RoleType.MANAGER)
    await emp_repo.save(employee)
    await db.commit()

    # Get the newly added role to return the details
    manager_role = next(
        (
            r
            for r in employee.roles
            if r.tenant_id == schema.tenant_id and r.role_type == RoleType.MANAGER
        ),
        None,
    )
    return {
        "id": employee.id,
        "name": employee.name,
        "email": str(employee.email),
        "tenant_id": schema.tenant_id,
        "is_active": manager_role.is_active if manager_role else True,
    }


@router.delete("/managers/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_manager(
    employee_id: int,
    db: DbSession,
    _: CurrentAdminEmployee,
) -> None:
    emp_repo = SQLAlchemyEmployeeRepository(db)
    employee = await emp_repo.find_by_id(employee_id)
    if not employee:
        raise DomainException("Employee not found", status_code=404)

    employee.roles = [r for r in employee.roles if r.role_type != RoleType.MANAGER]
    await emp_repo.save(employee)
    await db.commit()


@router.get("/analytics/global", status_code=status.HTTP_200_OK)
async def get_global_analytics(
    mongo: MongoDB,
    _: CurrentAdminEmployee,
    limit: int = 5,
    sort: str = "revenue",
) -> list[dict[str, Any]]:
    query = GetGlobalAnalyticsQuery(limit=limit, sort_by=sort)
    return await handle_get_global_analytics(query, mongo)


@router.get("/analytics/export")
async def export_analytics(
    mongo: MongoDB,
    _: CurrentAdminEmployee,
    tenant_id: str | None = None,
) -> StreamingResponse:
    logger.info("Executando consulta: ExportAnalyticsQuery(tenant_id=%r)", tenant_id)
    # Fetch data (mocking data fetch for export)
    filter_query = {"tenant_id": tenant_id} if tenant_id else {}
    cursor = mongo["orders_read"].find(filter_query)
    data = await cursor.to_list(length=1000)
    logger.info("Resultado da consulta ExportAnalyticsQuery: %s", data)

    # Generate CSV in-memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["order_id", "tenant_id", "total", "created_at"])
    for row in data:
        writer.writerow(
            [row.get("order_id"), row.get("tenant_id"), row.get("total"), row.get("created_at")]
        )

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=analytics.csv"},
    )
