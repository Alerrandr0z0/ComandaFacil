# 07 — OOP Avançado: Dunder Methods, Metaclasses e Descritores

## Dunder Methods Completos

### Representação

```python
class Vetor:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def __repr__(self) -> str:
        """Para desenvolvedores — deve ser eval()-ável quando possível."""
        return f"Vetor({self.x!r}, {self.y!r})"

    def __str__(self) -> str:
        """Para usuário final — mais legível."""
        return f"({self.x}, {self.y})"

    def __format__(self, spec: str) -> str:
        """Suporta f-string com format spec: f'{v:.2f}'"""
        if spec == "polar":
            import math
            r = math.sqrt(self.x**2 + self.y**2)
            theta = math.atan2(self.y, self.x)
            return f"r={r:.2f}, θ={math.degrees(theta):.1f}°"
        return f"({self.x:{spec}}, {self.y:{spec}})"
```

### Operadores Aritméticos

```python
class Vetor:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def __add__(self, other: "Vetor") -> "Vetor":
        return Vetor(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Vetor") -> "Vetor":
        return Vetor(self.x - other.x, self.y - other.y)

    def __mul__(self, escalar: float) -> "Vetor":
        return Vetor(self.x * escalar, self.y * escalar)

    def __rmul__(self, escalar: float) -> "Vetor":
        """Chamado quando o lado esquerdo não sabe como multiplicar."""
        return self.__mul__(escalar)

    def __neg__(self) -> "Vetor":
        return Vetor(-self.x, -self.y)

    def __abs__(self) -> float:
        import math
        return math.sqrt(self.x**2 + self.y**2)

    def __bool__(self) -> bool:
        return abs(self) > 0

    # Operadores in-place
    def __iadd__(self, other: "Vetor") -> "Vetor":
        self.x += other.x
        self.y += other.y
        return self

v1 = Vetor(1, 2)
v2 = Vetor(3, 4)
print(v1 + v2)      # Vetor(4, 6)
print(3 * v1)       # Vetor(3, 6) — usa __rmul__
```

### Container Protocol

```python
from typing import Iterator, Any

class Pilha:
    def __init__(self) -> None:
        self._itens: list[Any] = []

    def __len__(self) -> int:
        return len(self._itens)

    def __contains__(self, item: object) -> bool:
        return item in self._itens

    def __iter__(self) -> Iterator[Any]:
        return iter(reversed(self._itens))  # LIFO

    def __getitem__(self, index: int) -> Any:
        return self._itens[-(index + 1)]  # índice 0 = topo

    def __bool__(self) -> bool:
        return bool(self._itens)

    def push(self, item: Any) -> None:
        self._itens.append(item)

    def pop(self) -> Any:
        return self._itens.pop()

p = Pilha()
p.push(1); p.push(2); p.push(3)
print(len(p))        # 3
print(2 in p)        # True
print(list(p))       # [3, 2, 1]
```

### Context Manager Protocol

```python
from types import TracebackType

class GerenciadorRecurso:
    def __init__(self, nome: str) -> None:
        self.nome = nome
        self._recurso: object = None

    def __enter__(self) -> "GerenciadorRecurso":
        print(f"Abrindo {self.nome}")
        self._recurso = object()  # simula abertura
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        print(f"Fechando {self.nome}")
        self._recurso = None
        # Retorne True para suprimir a exceção; False para propagar
        return False

with GerenciadorRecurso("arquivo.txt") as r:
    print(f"Usando {r.nome}")
```

---

## Metaclasses — Use com Moderação

> "Metaclasses são magia negra para 99% dos casos.
>  Se você precisa de uma, quase sempre há uma alternativa melhor."
>  — Tim Peters (parafraseado)

**Alternativas antes de usar metaclasse:**
1. `__init_subclass__` — para hooks na criação de subclasses
2. `__class_getitem__` — para customizar `Class[T]`
3. Class decorators — para modificar classes após criação
4. `ABC` — para interfaces

```python
# Quando metaclasse é justificada: framework, ORM, registro automático
class RegistradorMeta(type):
    _registro: dict[str, type] = {}

    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, object],
    ) -> "RegistradorMeta":
        cls = super().__new__(mcs, name, bases, namespace)
        if bases:  # não registra a própria classe base
            mcs._registro[name] = cls
        return cls

class Modelo(metaclass=RegistradorMeta):
    pass

class Usuario(Modelo):
    pass

class Produto(Modelo):
    pass

print(RegistradorMeta._registro)
# {'Usuario': <class 'Usuario'>, 'Produto': <class 'Produto'>}
```

---

## Descritores Avançados — Data vs Non-Data

```python
from typing import Any, TypeVar, Generic, overload

T = TypeVar("T")

class TipizadoCampo(Generic[T]):
    """Descritor genérico com validação de tipo."""

    def __init__(self, tipo: type[T]) -> None:
        self._tipo = tipo
        self._nome_attr: str = ""

    def __set_name__(self, owner: type, name: str) -> None:
        self._nome_attr = f"_{name}_valor"

    @overload
    def __get__(self, obj: None, objtype: type) -> "TipizadoCampo[T]": ...
    @overload
    def __get__(self, obj: object, objtype: type) -> T: ...

    def __get__(self, obj: object | None, objtype: type) -> "T | TipizadoCampo[T]":
        if obj is None:
            return self
        value = getattr(obj, self._nome_attr, None)
        if value is None:
            raise AttributeError(f"Campo não inicializado")
        return value  # type: ignore[return-value]

    def __set__(self, obj: object, value: T) -> None:
        if not isinstance(value, self._tipo):
            raise TypeError(
                f"Esperado {self._tipo.__name__}, recebido {type(value).__name__}"
            )
        setattr(obj, self._nome_attr, value)

class Pessoa:
    nome = TipizadoCampo(str)
    idade = TipizadoCampo(int)

    def __init__(self, nome: str, idade: int) -> None:
        self.nome = nome    # usa TipizadoCampo.__set__
        self.idade = idade  # usa TipizadoCampo.__set__

p = Pessoa("Ana", 30)
# p.nome = 123  # TypeError: Esperado str, recebido int
```

---

## `__init_subclass__` — Alternativa Moderna a Metaclasse

```python
from typing import Any

class Validavel:
    """Mixin que garante que subclasses definem campos obrigatórios."""

    _campos_obrigatorios: tuple[str, ...] = ()

    def __init_subclass__(cls, campos: tuple[str, ...] = (), **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls._campos_obrigatorios = campos

    def validar(self) -> bool:
        return all(
            getattr(self, campo, None) is not None
            for campo in self._campos_obrigatorios
        )

class Produto(Validavel, campos=("nome", "preco", "estoque")):
    def __init__(self, nome: str, preco: float, estoque: int) -> None:
        self.nome = nome
        self.preco = preco
        self.estoque = estoque

p = Produto("Caneta", 2.50, 100)
print(p.validar())  # True
print(p._campos_obrigatorios)  # ('nome', 'preco', 'estoque')
```
