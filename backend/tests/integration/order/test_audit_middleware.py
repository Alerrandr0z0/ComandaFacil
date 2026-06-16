from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.application.audit_middleware import AuditMiddleware
from app.auth.infrastructure.orm_models import AuditLogORM
from app.order.application.commands import CancelOrderItemCommand, CancelOrderItemHandler
from app.order.domain.fulfillment import Table
from app.order.domain.order_form import OrderForm
from app.order.domain.order_item import OrderFormItem
from app.order.infrastructure.pg_repository import SQLAlchemyOrderRepository
from app.shared.actor_context import ActorInfo, current_actor_var
from app.shared.base_orm import Base
from app.shared.command_bus import CommandBus
from app.shared.middlewares import UnitOfWorkMiddleware
from app.shared.money import Money
from app.shared.tenant_context import tenant_context_var

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


@pytest.fixture
async def sqlite_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session
    await engine.dispose()


class TestAuditMiddlewareIntegration:
    """Integration tests for AuditMiddleware with CommandBus + SQLite."""

    @pytest.mark.asyncio
    async def test_audit_when_command_succeeds_then_log_persisted(
        self,
        sqlite_session: AsyncSession,
    ) -> None:
        """Should persist an AuditLogORM row when command completes successfully."""
        # Arrange
        repo = SQLAlchemyOrderRepository(sqlite_session)
        order = OrderForm(id=300, tenant_id="franquia_001", display_code="MESA-30")
        order.set_fulfillment_strategy(Table(30))
        item = OrderFormItem(
            id=3001,
            menu_item_id=10,
            name_cpy="Pizza",
            price_cpy=Money(Decimal("39.90")),
            station_type_cpy="Grill",
            quantity=2,
        )
        order.add_item(item)
        await repo.save(order)
        await sqlite_session.commit()

        handler = CancelOrderItemHandler(SQLAlchemyOrderRepository(sqlite_session))
        bus = CommandBus(
            handlers={CancelOrderItemCommand: handler},
            middlewares=[
                AuditMiddleware(sqlite_session),
                UnitOfWorkMiddleware(sqlite_session),
            ],
        )

        tenant_token = tenant_context_var.set("franquia_001")
        actor_token = current_actor_var.set(ActorInfo(id=10, name="Maria"))

        # Act
        result = await bus.dispatch(
            CancelOrderItemCommand(order_id=300, item_id=3001, tenant_id="franquia_001")
        )

        # Assert — handler result
        canceled_item = next(i for i in result.items if i.id == 3001)
        assert canceled_item.status.value == "CANCELED"

        # Assert — audit log persisted
        result_sql = await sqlite_session.execute(
            select(AuditLogORM).where(AuditLogORM.action == "CANCEL_ORDER_ITEM")
        )
        log_entry = result_sql.scalar_one_or_none()
        assert log_entry is not None
        assert log_entry.actor_id == 10
        assert log_entry.actor_name == "Maria"
        assert log_entry.entity_id == "300"
        assert log_entry.entity_type == "order"
        assert "CancelOrderItemCommand(order_id=300" in log_entry.details

        tenant_context_var.reset(tenant_token)
        current_actor_var.reset(actor_token)

    @pytest.mark.asyncio
    async def test_audit_when_handler_fails_then_log_not_persisted(
        self,
        sqlite_session: AsyncSession,
    ) -> None:
        """Should NOT persist an AuditLogORM row when handler raises."""
        # Arrange
        repo = SQLAlchemyOrderRepository(sqlite_session)
        order = OrderForm(id=400, tenant_id="franquia_001", display_code="MESA-40")
        order.set_fulfillment_strategy(Table(40))
        item = OrderFormItem(
            id=4001,
            menu_item_id=10,
            name_cpy="Pizza",
            price_cpy=Money(Decimal("39.90")),
            station_type_cpy="Grill",
            quantity=1,
        )
        order.add_item(item)
        await repo.save(order)
        await sqlite_session.commit()

        handler = CancelOrderItemHandler(SQLAlchemyOrderRepository(sqlite_session))
        bus = CommandBus(
            handlers={CancelOrderItemCommand: handler},
            middlewares=[
                AuditMiddleware(sqlite_session),
                UnitOfWorkMiddleware(sqlite_session),
            ],
        )

        tenant_token = tenant_context_var.set("franquia_001")
        current_actor_var.set(ActorInfo(id=10, name="Maria"))

        # Act — cancel item that doesn't exist in order
        with pytest.raises(Exception, match="não encontrado"):
            await bus.dispatch(
                CancelOrderItemCommand(order_id=400, item_id=9999, tenant_id="franquia_001")
            )

        # Assert — audit log NOT persisted (rolled back by UnitOfWorkMiddleware)
        result_sql = await sqlite_session.execute(
            select(AuditLogORM).where(AuditLogORM.action == "CANCEL_ORDER_ITEM")
        )
        rows = result_sql.all()
        assert len(rows) == 0

        tenant_context_var.reset(tenant_token)

    @pytest.mark.asyncio
    async def test_audit_when_no_actor_context_then_logs_system(
        self,
        sqlite_session: AsyncSession,
    ) -> None:
        """Should log 'System' as actor_name when no actor context is set."""
        # Arrange
        repo = SQLAlchemyOrderRepository(sqlite_session)
        order = OrderForm(id=500, tenant_id="franquia_001", display_code="MESA-50")
        order.set_fulfillment_strategy(Table(50))
        item = OrderFormItem(
            id=5001,
            menu_item_id=10,
            name_cpy="Suco",
            price_cpy=Money(Decimal("8.50")),
            station_type_cpy="Beverage",
            quantity=1,
        )
        order.add_item(item)
        await repo.save(order)
        await sqlite_session.commit()

        handler = CancelOrderItemHandler(SQLAlchemyOrderRepository(sqlite_session))
        bus = CommandBus(
            handlers={CancelOrderItemCommand: handler},
            middlewares=[
                AuditMiddleware(sqlite_session),
                UnitOfWorkMiddleware(sqlite_session),
            ],
        )

        tenant_token = tenant_context_var.set("franquia_001")
        current_actor_var.set(None)

        # Act
        await bus.dispatch(
            CancelOrderItemCommand(order_id=500, item_id=5001, tenant_id="franquia_001")
        )

        # Assert
        result_sql = await sqlite_session.execute(
            select(AuditLogORM).where(AuditLogORM.action == "CANCEL_ORDER_ITEM")
        )
        log_entry = result_sql.scalar_one_or_none()
        assert log_entry is not None
        assert log_entry.actor_id is None
        assert log_entry.actor_name == "System"

        tenant_context_var.reset(tenant_token)
