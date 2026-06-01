from __future__ import annotations

import datetime
from abc import ABC, abstractmethod
from typing import Final


class Session:
    """
    Session Entity representing active stateful user sessions in the database.

    Attributes:
        session_id: Unique session token string.
        employee_id: Reference ID of the employee associated with the session.
        tenant_id: Reference ID of the tenant franchise.
        expires_at: Expiration timestamp.
    """

    def __init__(self, session_id: str, employee_id: int, tenant_id: int, expires_at: datetime.datetime) -> None:
        self.session_id: Final[str] = session_id
        self.employee_id: Final[int] = employee_id
        self.tenant_id: Final[int] = tenant_id
        self.expires_at: datetime.datetime = expires_at

    def is_expired(self) -> bool:
        """Checks if the session has reached its expiration time."""
        now = datetime.datetime.now(datetime.UTC)
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=datetime.UTC)
        return now >= expires

    def __repr__(self) -> str:
        return f"{type(self).__name__}(session_id={self.session_id!r}, employee_id={self.employee_id}, tenant_id={self.tenant_id}, expires_at={self.expires_at!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Session):
            return NotImplemented
        return self.session_id == other.session_id

    def __hash__(self) -> int:
        return hash(self.session_id)


class SessionRepository(ABC):
    """Abstract Repository Interface for Session Entity."""

    @abstractmethod
    async def find_by_id(self, session_id: str) -> Session | None:
        """Retrieves a Session by its session ID."""

    @abstractmethod
    async def save(self, session: Session) -> None:
        """Saves a Session in persistent storage."""

    @abstractmethod
    async def invalidate(self, session_id: str) -> None:
        """Invalidates/removes a Session from persistent storage."""
