from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from app.auth.domain.employee import Employee, EmployeeRepository
from app.auth.domain.session import Session, SessionRepository
from app.shared.value_objects import Email


@dataclass(frozen=True)
class GetEmployeeQuery:
    """Query to fetch an Employee by their email."""
    email: str

    def __repr__(self) -> str:
        return f"GetEmployeeQuery(email={self.email!r})"


class GetEmployeeHandler:
    """Handler to execute the GetEmployee query."""

    def __init__(self, employee_repo: EmployeeRepository) -> None:
        self._employee_repo: Final[EmployeeRepository] = employee_repo

    async def handle(self, query: GetEmployeeQuery) -> Employee | None:
        """Retrieves an Employee aggregate by email, returning None if not found."""
        email_vo = Email(query.email)
        return await self._employee_repo.find_by_email(email_vo)

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"


@dataclass(frozen=True)
class GetSessionQuery:
    """Query to fetch a Session by its session ID."""
    session_id: str

    def __repr__(self) -> str:
        return f"GetSessionQuery(session_id={self.session_id!r})"


class GetSessionHandler:
    """Handler to execute the GetSession query."""

    def __init__(self, session_repo: SessionRepository) -> None:
        self._session_repo: Final[SessionRepository] = session_repo

    async def handle(self, query: GetSessionQuery) -> Session | None:
        """Retrieves a Session entity by its session ID, returning None if not found."""
        return await self._session_repo.find_by_id(query.session_id)

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"
