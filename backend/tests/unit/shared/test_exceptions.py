from http import HTTPStatus

from app.shared.exceptions import DomainException, ForbiddenError


def test_forbidden_error_default_message() -> None:
    exc = ForbiddenError()
    assert exc.message == "Acesso não autorizado."
    assert exc.status_code == HTTPStatus.FORBIDDEN


def test_domain_exception_creation() -> None:
    exc = DomainException("Erro", HTTPStatus.BAD_REQUEST)
    assert exc.message == "Erro"
    assert exc.status_code == HTTPStatus.BAD_REQUEST
