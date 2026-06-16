from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

logger = logging.getLogger("app.shared.command_bus")


class ICommandHandler(Protocol):
    """Protocol for command handlers.

    Implementations must provide:
        async def handle(self, command: Any) -> Any
    """

    async def handle(self, command: Any) -> Any: ...


class IMiddleware(Protocol):
    """Protocol for command bus middleware/behavior.

    Implementations must provide:
        async def __call__(self, command: Any, next_: Callable[[Any], Awaitable[Any]], bus: CommandBus) -> Any
    """

    async def __call__(
        self,
        command: Any,
        next_: Callable[[Any], Awaitable[Any]],
        bus: CommandBus,
    ) -> Any: ...


@dataclass
class CommandBus:
    """Central command bus with middleware pipeline support.

    Usage:
        bus = CommandBus(handlers={MyCommand: MyHandler()})
        result = await bus.dispatch(MyCommand(...))
    """

    handlers: dict[type, ICommandHandler] = field(default_factory=dict)
    middlewares: list[IMiddleware] = field(default_factory=list)

    async def dispatch(self, command: Any) -> Any:
        """Dispatches a command through the middleware pipeline to its handler."""
        handler = self.handlers.get(type(command))
        if handler is None:
            raise ValueError(f"No handler registered for {type(command).__name__}")

        async def core(cmd: Any) -> Any:
            return await handler.handle(cmd)

        if not self.middlewares:
            return await core(command)

        chain = self._build_pipeline(core, 0)

        return await chain(command)

    def _build_pipeline(
        self,
        core: Callable[[Any], Awaitable[Any]],
        index: int,
    ) -> Callable[[Any], Awaitable[Any]]:
        if index >= len(self.middlewares):
            return core

        middleware = self.middlewares[index]
        next_ = self._build_pipeline(core, index + 1)

        async def wrapped(command: Any) -> Any:
            return await middleware(command, next_, self)

        return wrapped

    def __repr__(self) -> str:
        return f"CommandBus(handlers={len(self.handlers)}, middlewares={len(self.middlewares)})"
