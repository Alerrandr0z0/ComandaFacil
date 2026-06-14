from contextvars import ContextVar
from dataclasses import dataclass


@dataclass(frozen=True)
class ActorInfo:
    """Information about the current authenticated user/employee executing the request."""

    id: int
    name: str


current_actor_var: ContextVar[ActorInfo | None] = ContextVar("current_actor", default=None)
