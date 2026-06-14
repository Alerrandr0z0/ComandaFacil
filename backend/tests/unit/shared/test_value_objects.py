import pytest

from app.shared.value_objects import Address, Email


def test_invalid_email_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Email inválido"):
        Email("invalid-email")


def test_address_empty_fields_raise_value_error() -> None:
    with pytest.raises(ValueError, match="não pode ser vazio"):
        Address("", "123", "Bairro", "Cidade", "ST", "12345678")


def test_address_invalid_cep_raises_value_error() -> None:
    with pytest.raises(ValueError, match="CEP inválido"):
        Address("Rua A", "123", "Bairro", "Cidade", "ST", "123")


def test_address_str_method() -> None:
    addr = Address("Rua A", "123", "Bairro", "Cidade", "ST", "12345678")
    assert str(addr) == "Rua A, 123 - Bairro, Cidade/ST (12345678)"
