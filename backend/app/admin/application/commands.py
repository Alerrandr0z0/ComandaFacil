from dataclasses import dataclass

from app.auth.domain.tenant import PlanType, Tenant, TenantRepository


@dataclass
class CreateTenantCommand:
    name: str
    plan_type: PlanType


async def handle_create_tenant(command: CreateTenantCommand, repo: TenantRepository) -> Tenant:
    # MVP simple ID generation logic
    all_tenants = await repo.find_all()
    new_id = max([t.id for t in all_tenants], default=0) + 1
    tenant = Tenant(id=new_id, name=command.name, plan_type=command.plan_type)
    await repo.save(tenant)
    return tenant


@dataclass
class DeleteTenantCommand:
    tenant_id: int


async def handle_delete_tenant(command: DeleteTenantCommand, repo: TenantRepository) -> None:
    # Basic check to prevent deleting main tenant if needed
    if command.tenant_id == 1:
        raise ValueError("Cannot delete main tenant.")
    await repo.delete(command.tenant_id)
