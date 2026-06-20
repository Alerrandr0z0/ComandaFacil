from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.domain.employee import Employee
from app.auth.domain.tenant import PlanType, Tenant
from app.dependencies import db_session, get_current_admin_employee
from app.main import app
from app.shared.base_orm import Base
from app.shared.value_objects import Email

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


@pytest.fixture()
async def sqlite_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session
        await session.rollback()
    await engine.dispose()


@pytest.fixture()
async def cliente_api(sqlite_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Cliente HTTP que sobrescreve dependências para usar SQLite em memória e um admin simulado."""
    admin_mock = Employee.create(
        id=999,
        name="Admin Sistema",
        email=Email("admin@comandafacil.com"),
        password="senha_segura_123",
    )

    async def sobrescrever_db_session() -> AsyncGenerator[AsyncSession, None]:
        yield sqlite_session

    async def sobrescrever_get_current_admin_employee() -> Employee:
        return admin_mock

    app.dependency_overrides[db_session] = sobrescrever_db_session
    app.dependency_overrides[get_current_admin_employee] = sobrescrever_get_current_admin_employee

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", headers={"X-Tenant-ID": "1"}
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.mark.asyncio()
async def test_rotas_crud_tenant_quando_operacoes_executadas_entao_persiste_dados_corretamente(
    cliente_api: AsyncClient, sqlite_session: AsyncSession
) -> None:
    # Semeia o tenant principal ID 1 (protegido)
    from app.auth.infrastructure.repositories import SQLAlchemyTenantRepository

    tenant_repo = SQLAlchemyTenantRepository(sqlite_session)
    tenant_principal = Tenant(id=1, name="Tenant Principal", plan_type=PlanType.PLUS)
    await tenant_repo.save(tenant_principal)
    await sqlite_session.commit()

    # 1. Criar novo tenant (deve receber ID 2)
    resposta = await cliente_api.post(
        "/api/v1/admin/tenants",
        json={
            "name": "Franquia Z",
            "plan_type": "PRO",
        },
    )
    assert resposta.status_code == 201
    dados_resposta = resposta.json()
    assert dados_resposta["id"] == 2
    assert dados_resposta["name"] == "Franquia Z"
    assert dados_resposta["plan_type"] == "PRO"
    assert dados_resposta["is_active"] is True

    # 2. Listar tenants (deve retornar ambos)
    resposta_lista = await cliente_api.get("/api/v1/admin/tenants")
    assert resposta_lista.status_code == 200
    tenants = resposta_lista.json()
    assert len(tenants) == 2
    assert any(t["name"] == "Franquia Z" for t in tenants)

    # 3. Deletar tenant Z (ID 2)
    resposta_deletar = await cliente_api.delete(f"/api/v1/admin/tenants/{dados_resposta['id']}")
    assert resposta_deletar.status_code == 204

    # Verificar exclusão do DB
    resposta_lista_depois = await cliente_api.get("/api/v1/admin/tenants")
    assert resposta_lista_depois.status_code == 200
    assert len(resposta_lista_depois.json()) == 1
    assert resposta_lista_depois.json()[0]["id"] == 1


@pytest.mark.asyncio()
async def test_rotas_crud_gerente_quando_operacoes_executadas_entao_gerencia_role_corretamente(
    cliente_api: AsyncClient, sqlite_session: AsyncSession
) -> None:
    # Configuração - Registra o tenant primeiro
    await cliente_api.post(
        "/api/v1/admin/tenants",
        json={
            "name": "Franquia Y",
            "plan_type": "BASIC",
        },
    )

    # 1. Criar um gerente
    resposta = await cliente_api.post(
        "/api/v1/admin/managers",
        json={
            "name": "Gerente Silva",
            "email": "silva@franquia.com",
            "password": "gerente_senha_123",
            "tenant_id": 1,
        },
    )
    assert resposta.status_code == 201
    dados_resposta = resposta.json()
    assert dados_resposta["name"] == "Gerente Silva"
    assert dados_resposta["email"] == "silva@franquia.com"
    assert dados_resposta["tenant_id"] == 1
    assert dados_resposta["is_active"] is True
    gerente_employee_id = dados_resposta["id"]

    # 2. Listar gerentes
    resposta_lista = await cliente_api.get("/api/v1/admin/managers")
    assert resposta_lista.status_code == 200
    gerentes = resposta_lista.json()
    assert len(gerentes) == 1
    assert gerentes[0]["name"] == "Gerente Silva"
    assert gerentes[0]["tenant_id"] == 1

    # 3. Deletar gerente
    resposta_deletar = await cliente_api.delete(f"/api/v1/admin/managers/{gerente_employee_id}")
    assert resposta_deletar.status_code == 204

    # Verificar que o gerente/vínculo foi excluído do DB
    resposta_lista_depois = await cliente_api.get("/api/v1/admin/managers")
    assert resposta_lista_depois.status_code == 200
    assert len(resposta_lista_depois.json()) == 0
