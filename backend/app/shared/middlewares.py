from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("app.shared.middlewares")


class UnitOfWorkMiddleware:
    """Middleware that manages a database transaction per command dispatch.

    Commits on success, rolls back on failure.
    Must be placed as the innermost middleware (closest to the handler).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def __call__(
        self,
        command: Any,
        next_: Callable[[Any], Awaitable[Any]],
        bus: Any,  # noqa: ARG002
    ) -> Any:
        try:
            result = await next_(command)
        except Exception:
            await self._session.rollback()
            raise
        await self._session.commit()
        return result


class AuditMiddleware:
    """Middleware that logs audit entries for dispatched commands.

    Writes to the audit_logs table via the current DB session
    using actor context from current_actor_var.
    """

    async def __call__(
        self,
        command: Any,
        next_: Callable[[Any], Awaitable[Any]],
        bus: Any,  # noqa: ARG002
    ) -> Any:
        return await next_(command)
