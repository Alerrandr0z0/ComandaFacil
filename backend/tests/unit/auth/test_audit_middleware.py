from __future__ import annotations

from unittest.mock import AsyncMock

from app.auth.application.audit_middleware import AuditMiddleware
from app.shared.actor_context import ActorInfo, current_actor_var
from app.shared.tenant_context import tenant_context_var


class TestAuditMiddlewareUnit:
    """Unit tests for AuditMiddleware using AsyncMock session."""

    async def test_audit_when_command_dispatched_then_writes_audit_log(self) -> None:
        """Should add an AuditLogORM entry with correct fields before next_."""
        session = AsyncMock()
        middleware = AuditMiddleware(session)

        tenant_token = tenant_context_var.set("tenant_001")
        actor_token = current_actor_var.set(ActorInfo(id=42, name="João"))

        class FakeOrderCommand:
            order_id = 1001

            def __repr__(self) -> str:
                return "FakeOrderCommand(order_id=1001)"

        async def next_(cmd: object) -> str:
            return "ok"

        result = await middleware(FakeOrderCommand(), next_, None)

        session.add.assert_called_once()
        log_entry = session.add.call_args[0][0]
        assert log_entry.action == "FAKE_ORDER"
        assert log_entry.entity_type == "order"
        assert log_entry.entity_id == "1001"
        assert log_entry.actor_id == 42
        assert log_entry.actor_name == "João"
        assert result == "ok"

        tenant_context_var.reset(tenant_token)
        current_actor_var.reset(actor_token)

    async def test_audit_when_no_actor_then_uses_system(self) -> None:
        """Should default actor_name to 'System' and actor_id to None."""
        session = AsyncMock()
        middleware = AuditMiddleware(session)

        tenant_token = tenant_context_var.set("tenant_001")
        current_actor_var.set(None)

        class FakeCmd:
            order_id = 999

        async def next_(cmd: object) -> str:
            return "ok"

        await middleware(FakeCmd(), next_, None)

        log_entry = session.add.call_args[0][0]
        assert log_entry.actor_id is None
        assert log_entry.actor_name == "System"

        tenant_context_var.reset(tenant_token)

    async def test_audit_when_command_has_id_field_then_entity_id_falls_back(self) -> None:
        """Should use command.id if order_id is not present."""
        session = AsyncMock()
        middleware = AuditMiddleware(session)

        tenant_token = tenant_context_var.set("tenant_001")
        actor_token = current_actor_var.set(ActorInfo(id=1, name="Test"))

        class FakeCmd:
            id = 777

        async def next_(cmd: object) -> str:
            return "ok"

        await middleware(FakeCmd(), next_, None)

        log_entry = session.add.call_args[0][0]
        assert log_entry.entity_id == "777"
        assert log_entry.entity_type is None

        tenant_context_var.reset(tenant_token)
        current_actor_var.reset(actor_token)

    async def test_audit_when_no_tenant_then_converts_empty_string(self) -> None:
        """Should handle empty tenant_id gracefully."""
        session = AsyncMock()
        middleware = AuditMiddleware(session)

        actor_token = current_actor_var.set(ActorInfo(id=1, name="Test"))

        class FakeCmd:
            order_id = 10

        async def next_(cmd: object) -> str:
            return "ok"

        tenant_token = tenant_context_var.set("")
        await middleware(FakeCmd(), next_, None)
        tenant_context_var.reset(tenant_token)
        current_actor_var.reset(actor_token)

        log_entry = session.add.call_args[0][0]
        assert log_entry.tenant_id >= 0
        assert log_entry.actor_id == 1
