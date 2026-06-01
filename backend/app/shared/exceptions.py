from http import HTTPStatus


class DomainException(Exception):
    """Base class for all domain exceptions."""

    def __init__(self, message: str, status_code: int = HTTPStatus.BAD_REQUEST) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(DomainException):
    def __init__(self, resource: str, identifier: str | int) -> None:
        super().__init__(
            message=f"{resource} '{identifier}' não encontrado.",
            status_code=HTTPStatus.NOT_FOUND,
        )


class ConflictError(DomainException):
    def __init__(self, message: str) -> None:
        super().__init__(message=message, status_code=HTTPStatus.CONFLICT)


class ForbiddenError(DomainException):
    def __init__(self, message: str = "Acesso não autorizado.") -> None:
        super().__init__(message=message, status_code=HTTPStatus.FORBIDDEN)


class InsufficientStockError(DomainException):
    def __init__(self, item_name: str, available: float, requested: float) -> None:
        message = (
            f"Estoque insuficiente para '{item_name}': "
            f"disponível={available}, solicitado={requested}."
        )
        super().__init__(
            message=message,
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        )
