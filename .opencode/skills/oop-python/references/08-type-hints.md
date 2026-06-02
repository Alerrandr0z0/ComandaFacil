# 08 — Type Hints em OOP Python Moderno

## Anotações de Classe Completas

```python
from typing import ClassVar, Final, TYPE_CHECKING
from collections.abc import Iterator, Callable

if TYPE_CHECKING:
    from pathlib import Path  # evita import circular em runtime

class Servidor:
    # Constante de classe — imutável por convenção de tipo
    VERSAO: Final[str] = "2.0.0"

    # Atributo de classe tipado
    _instancias: ClassVar[list["Servidor"]] = []

    def __init__(
        self,
        host: str,
        porta: int = 8080,
        middlewares: list[Callable[[str], str]] | None = None,
    ) -> None:
        self.host: str = host
        self.porta: int = porta
        self._middlewares: list[Callable[[str], str]] = middlewares or []
        Servidor._instancias.append(self)

    def __iter__(self) -> Iterator[Callable[[str], str]]:
        return iter(self._middlewares)
```

---

## Generics em Classes (Python 3.12+ nativo)

```python
# Python 3.12+ — sintaxe limpa com type parameter syntax
class Pilha[T]:
    def __init__(self) -> None:
        self._itens: list[T] = []

    def push(self, item: T) -> None:
        self._itens.append(item)

    def pop(self) -> T:
        return self._itens.pop()

    def peek(self) -> T | None:
        return self._itens[-1] if self._itens else None

# Python 3.9-3.11 — usando TypeVar
from typing import TypeVar, Generic

T = TypeVar("T")

class PilhaCompat(Generic[T]):
    def __init__(self) -> None:
        self._itens: list[T] = []

    def push(self, item: T) -> None:
        self._itens.append(item)

    def pop(self) -> T:
        return self._itens.pop()

# Uso com type checkers
pilha_int: Pilha[int] = Pilha()
pilha_int.push(42)
pilha_str: Pilha[str] = Pilha()
pilha_str.push("hello")
```

---

## Bounded TypeVar e Constrained TypeVar

```python
from typing import TypeVar
from numbers import Number

# TypeVar limitado a uma hierarquia
Numerico = TypeVar("Numerico", bound=Number)

class Calculadora(Generic[Numerico]):
    def __init__(self, valor: Numerico) -> None:
        self.valor = valor

    def dobrar(self) -> Numerico:
        return self.valor * 2  # type: ignore[return-value]

# TypeVar restrito a tipos específicos
T_Str_Bytes = TypeVar("T_Str_Bytes", str, bytes)

def primeira_letra(texto: T_Str_Bytes) -> T_Str_Bytes:
    return texto[:1]  # type: ignore[return-value]
```

---

## Self Type — Métodos que Retornam a Própria Instância

```python
# Python 3.11+ — typing.Self
from typing import Self

class Construtor:
    def __init__(self) -> None:
        self._config: dict[str, object] = {}

    def com_host(self, host: str) -> Self:
        self._config["host"] = host
        return self

    def com_porta(self, porta: int) -> Self:
        self._config["porta"] = porta
        return self

    def construir(self) -> dict[str, object]:
        return self._config.copy()

class ConstrutorExtendido(Construtor):
    def com_ssl(self, ativo: bool) -> Self:  # retorna ConstrutorExtendido, não Construtor
        self._config["ssl"] = ativo
        return self

# Fluent interface com type safety
config = (ConstrutorExtendido()
          .com_host("localhost")
          .com_porta(8443)
          .com_ssl(True)
          .construir())
```

---

## `overload` — Múltiplas Assinaturas

```python
from typing import overload

class Processador:
    @overload
    def processar(self, entrada: str) -> str: ...
    @overload
    def processar(self, entrada: list[str]) -> list[str]: ...
    @overload
    def processar(self, entrada: int) -> int: ...

    def processar(self, entrada: str | list[str] | int) -> str | list[str] | int:
        if isinstance(entrada, str):
            return entrada.upper()
        elif isinstance(entrada, list):
            return [s.upper() for s in entrada]
        else:
            return entrada * 2
```

---

## Protocol com TypeVar (Covariância)

```python
from typing import Protocol, TypeVar

T_co = TypeVar("T_co", covariant=True)  # covariant: retorno

class Produtor(Protocol[T_co]):
    def produzir(self) -> T_co: ...

class ProducaoInt:
    def produzir(self) -> int:
        return 42

# ProducaoInt satisfaz Produtor[int]
# e também Produtor[float] por covariância (int é subtipo de float)
```

---

## TypeGuard e TypeIs — Narrowing em Métodos

```python
from typing import TypeGuard, TypeIs

class Validador:
    @staticmethod
    def eh_string_valida(valor: object) -> TypeGuard[str]:
        """Type guard: após essa checagem, o type checker sabe que valor é str."""
        return isinstance(valor, str) and len(valor) > 0

    @staticmethod
    def eh_inteiro(valor: object) -> TypeIs[int]:
        """TypeIs (Python 3.13+): mais preciso que TypeGuard."""
        return isinstance(valor, int) and not isinstance(valor, bool)

def processar(entrada: str | int | None) -> str:
    if Validador.eh_string_valida(entrada):
        return entrada.upper()  # type checker sabe que é str aqui
    return str(entrada)
```

---

## Configuração de mypy para Projetos OOP

```ini
# mypy.ini
[mypy]
python_version = 3.12
strict = true                   # ativa todas as checagens
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
```

```toml
# pyproject.toml (alternativa moderna)
[tool.mypy]
python_version = "3.12"
strict = true
```

**Ferramentas recomendadas:**
- `mypy` — verificador estático padrão da indústria
- `pyright` — mais rápido, usado pelo VS Code (Pylance)
- `beartype` — validação de tipos em runtime com decorator
