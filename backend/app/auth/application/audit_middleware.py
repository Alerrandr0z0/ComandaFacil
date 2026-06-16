from __future__ import annotations

import hashlib
import logging
import re
from typing import TYPE_CHECKING, Any

from app.auth.infrastructure.orm_models import AuditLogORM
from app.shared.actor_context import current_actor_var
from app.shared.tenant_context import tenant_context_var

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("app.auth.audit_middleware")


def _command_to_action(command: Any) -> str:
    """Convert a command class name to an audit action string.

    CancelOrderItemCommand -> CANCEL_ORDER_ITEM
    """
    name = type(command).__name__
    name = name.removesuffix("Command")
    return re.sub(r"(?<=[a-z])(?=[A-Z])", "_", name).upper()


def _tenant_id_to_int(tenant_id: str) -> int:
    """Convert a string tenant_id to an int compatible with AuditLogORM FK."""
    try:
        return int(tenant_id)
    except ValueError:
        return int(hashlib.sha256(tenant_id.encode("utf-8")).hexdigest(), 16) % 1000000


def _extract_entity_info(command: Any) -> tuple[str | None, str]:
    """Extract (entity_type, entity_id) from a command using common field names."""
    entity_id = getattr(command, "order_id", getattr(command, "id", None))
    if entity_id is not None:
        return ("order" if hasattr(command, "order_id") else None), str(entity_id)
    return None, ""


class AuditMiddleware:
    """Middleware that writes an AuditLogORM entry for every dispatched command.

    Writes to the injected session before the inner pipeline runs,
    so the entry participates in the same UnitOfWork transaction.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def __call__(
        self,
        command: Any,
        next_: Callable[[Any], Awaitable[Any]],
        bus: Any,  # noqa: ARG002
    ) -> Any:
        actor = current_actor_var.get(None)
        tenant_id = tenant_context_var.get("")

        action = _command_to_action(command)
        entity_type, entity_id = _extract_entity_info(command)

        log_entry = AuditLogORM(
            tenant_id=_tenant_id_to_int(tenant_id),
            actor_id=actor.id if actor else None,
            actor_name=actor.name if actor else "System",
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=repr(command),
        )
        self._session.add(log_entry)

        return await next_(command)
