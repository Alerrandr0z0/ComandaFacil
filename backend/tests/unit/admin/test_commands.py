import pytest

from app.admin.application.commands import (
    CreateTenantCommand,
    DeleteTenantCommand,
    handle_create_tenant,
    handle_delete_tenant,
)
from app.auth.domain.tenant import PlanType, Tenant, TenantRepository


class RepositorioTenantEmMemoria(TenantRepository):
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


@pytest.mark.asyncio()
async def test_criar_tenant_quando_dados_validos_entao_retorna_tenant_com_sucesso() -> None:
    repositorio = RepositorioTenantEmMemoria()
    comando = CreateTenantCommand(name="Franquia Teste", plan_type=PlanType.PRO)

    tenant = await handle_create_tenant(comando, repositorio)

    assert tenant.id == 1
    assert tenant.name == "Franquia Teste"
    assert tenant.plan_type == PlanType.PRO
    assert tenant.is_active_tenant() is True

    # Confirmar que foi salvo
    salvo = await repositorio.find_by_id(1)
    assert salvo is not None
    assert salvo.name == "Franquia Teste"


@pytest.mark.asyncio()
async def test_criar_tenant_quando_outras_existem_entao_incrementa_id() -> None:
    repositorio = RepositorioTenantEmMemoria()
    await repositorio.save(Tenant(id=5, name="Franquia Existente", plan_type=PlanType.BASIC))
    comando = CreateTenantCommand(name="Franquia Nova", plan_type=PlanType.PLUS)

    tenant = await handle_create_tenant(comando, repositorio)

    assert tenant.id == 6
    assert tenant.name == "Franquia Nova"
    assert tenant.plan_type == PlanType.PLUS


@pytest.mark.asyncio()
async def test_deletar_tenant_quando_id_for_1_entao_lanca_erro_e_protege_tenant_principal() -> None:
    repositorio = RepositorioTenantEmMemoria()
    await repositorio.save(Tenant(id=1, name="Tenant Principal", plan_type=PlanType.PLUS))
    comando = DeleteTenantCommand(tenant_id=1)

    with pytest.raises(ValueError, match=r"Cannot delete main tenant\."):
        await handle_delete_tenant(comando, repositorio)


@pytest.mark.asyncio()
async def test_deletar_tenant_quando_id_valido_entao_remove_com_sucesso() -> None:
    repositorio = RepositorioTenantEmMemoria()
    await repositorio.save(Tenant(id=2, name="Franquia para Deletar", plan_type=PlanType.BASIC))
    comando = DeleteTenantCommand(tenant_id=2)

    await handle_delete_tenant(comando, repositorio)

    assert await repositorio.find_by_id(2) is None
