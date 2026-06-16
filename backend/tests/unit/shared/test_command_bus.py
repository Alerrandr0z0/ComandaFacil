from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from app.shared.command_bus import CommandBus


@dataclass(frozen=True)
class FakeCommand:
    value: str


@dataclass(frozen=True)
class FakeResult:
    value: str


class FakeHandler:
    def __init__(self) -> None:
        self.called_with: Any = None

    async def handle(self, command: FakeCommand) -> FakeResult:
        self.called_with = command
        return FakeResult(value=f"processed:{command.value}")


class TestCommandBusDispatch:
    async def test_dispatch_when_handler_registered_then_calls_handler(self) -> None:
        # Arrange
        handler = FakeHandler()
        bus = CommandBus(handlers={FakeCommand: handler})
        command = FakeCommand(value="test")

        # Act
        result = await bus.dispatch(command)

        # Assert
        assert handler.called_with is command
        assert result.value == "processed:test"

    async def test_dispatch_when_no_handler_registered_then_raises_value_error(self) -> None:
        # Arrange
        bus = CommandBus(handlers={})

        # Act & Assert
        with pytest.raises(ValueError, match="No handler registered for"):
            await bus.dispatch(FakeCommand(value="test"))

    async def test_dispatch_when_middleware_configured_then_wraps_handler(self) -> None:
        # Arrange
        calls: list[str] = []

        class LoggingMiddleware:
            async def __call__(self, command: Any, next_: Any, bus: CommandBus) -> Any:
                calls.append("before")
                result = await next_(command)
                calls.append("after")
                return result

        handler = FakeHandler()
        bus = CommandBus(
            handlers={FakeCommand: handler},
            middlewares=[LoggingMiddleware()],
        )
        command = FakeCommand(value="test")

        # Act
        result = await bus.dispatch(command)

        # Assert
        assert calls == ["before", "after"]
        assert result.value == "processed:test"

    async def test_dispatch_when_multiple_middlewares_then_executes_in_order(self) -> None:
        # Arrange
        order: list[str] = []

        class MiddlewareA:
            async def __call__(self, command: Any, next_: Any, bus: CommandBus) -> Any:
                order.append("A_before")
                result = await next_(command)
                order.append("A_after")
                return result

        class MiddlewareB:
            async def __call__(self, command: Any, next_: Any, bus: CommandBus) -> Any:
                order.append("B_before")
                result = await next_(command)
                order.append("B_after")
                return result

        handler = FakeHandler()
        bus = CommandBus(
            handlers={FakeCommand: handler},
            middlewares=[MiddlewareA(), MiddlewareB()],
        )
        command = FakeCommand(value="test")

        # Act
        result = await bus.dispatch(command)

        # Assert
        assert order == ["A_before", "B_before", "B_after", "A_after"]
        assert result.value == "processed:test"

    async def test_dispatch_when_middleware_short_circuits_then_handler_not_called(self) -> None:
        # Arrange
        class BlockingMiddleware:
            async def __call__(self, command: Any, next_: Any, bus: CommandBus) -> Any:
                return FakeResult(value="blocked")

        handler = FakeHandler()
        bus = CommandBus(
            handlers={FakeCommand: handler},
            middlewares=[BlockingMiddleware()],
        )
        command = FakeCommand(value="test")

        # Act
        result = await bus.dispatch(command)

        # Assert
        assert handler.called_with is None
        assert result.value == "blocked"
