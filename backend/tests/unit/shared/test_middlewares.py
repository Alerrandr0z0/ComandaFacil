from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.shared.middlewares import AuditMiddleware, UnitOfWorkMiddleware


class TestUnitOfWorkMiddleware:
    async def test_uow_when_handler_succeeds_then_commits_session(self) -> None:
        # Arrange
        session = AsyncMock()
        middleware = UnitOfWorkMiddleware(session)

        async def next_(cmd: object) -> str:
            return "ok"

        # Act
        result = await middleware("cmd", next_, None)

        # Assert
        session.commit.assert_awaited_once()
        session.rollback.assert_not_called()
        assert result == "ok"

    async def test_uow_when_handler_fails_then_rolls_back_and_re_raises(self) -> None:
        # Arrange
        session = AsyncMock()
        middleware = UnitOfWorkMiddleware(session)

        async def next_(cmd: object) -> str:
            raise ValueError("handler failed")

        # Act & Assert
        with pytest.raises(ValueError, match="handler failed"):
            await middleware("cmd", next_, None)

        session.rollback.assert_awaited_once()
        session.commit.assert_not_called()


class TestAuditMiddleware:
    async def test_audit_when_handler_succeeds_then_passes_result_through(self) -> None:
        # Arrange
        middleware = AuditMiddleware()

        async def next_(cmd: object) -> str:
            return "ok"

        # Act
        result = await middleware("cmd", next_, None)

        # Assert
        assert result == "ok"
