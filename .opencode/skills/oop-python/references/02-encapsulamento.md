# 02 — Encapsulamento, Properties e Descritores

## Convenções de Visibilidade

```python
class Exemplo:
    publico: int        # acessível de qualquer lugar
    _protegido: int     # convenção: "use com cuidado, pode mudar"
    __privado: int      # name-mangling: _Exemplo__privado
```

| Prefixo | Nome | Acesso externo | Quando usar |
|---------|------|----------------|-------------|
| `nome` | Público | Livre | Interface pública da classe |
| `_nome` | Protegido | Por convenção bloqueado | Implementação interna, subclasses |
| `__nome` | Privado (mangled) | `obj._Classe__nome` | Evitar conflito em subclasses |

**Regra de ouro:** prefira `_` na maior parte dos casos. Use `__` apenas para evitar colisões
em hierarquias de herança — não como "segurança real".

---

## `@property` — O Modo Pythônico

```python
class Temperatura:
    def __init__(self, celsius: float) -> None:
        self._celsius: float = celsius  # armazenamento interno

    @property
    def celsius(self) -> float:
        return self._celsius

    @celsius.setter
    def celsius(self, valor: float) -> None:
        if valor < -273.15:
            raise ValueError(f"Temperatura abaixo do zero absoluto: {valor}")
        self._celsius = valor

    @celsius.deleter
    def celsius(self) -> None:
        del self._celsius

    @property
    def fahrenheit(self) -> float:
        """Propriedade computada — sem setter pois é derivada."""
        return self._celsius * 9/5 + 32

    @property
    def kelvin(self) -> float:
        return self._celsius + 273.15

# Uso limpo, sem getters/setters Java-style
t = Temperatura(25)
print(t.fahrenheit)   # 77.0
t.celsius = 100       # dispara o setter com validação
```

**Anti-pattern a evitar:**
```python
# ❌ Java-style — não faça isso em Python
class Ruim:
    def get_nome(self) -> str: return self._nome
    def set_nome(self, v: str) -> None: self._nome = v
```

---

## Propriedades Computadas com Cache

```python
from functools import cached_property

class Relatorio:
    def __init__(self, dados: list[int]) -> None:
        self._dados = dados

    @cached_property
    def media(self) -> float:
        """Calculado uma vez, depois em cache. Requer que a instância seja mutável."""
        print("Calculando média...")
        return sum(self._dados) / len(self._dados)

r = Relatorio([1, 2, 3, 4, 5])
print(r.media)  # "Calculando média..." → 3.0
print(r.media)  # 3.0 (do cache, sem recalcular)
```

**Nota:** `cached_property` não funciona em classes com `__slots__` ou `frozen=True`.

---

## Descritores — O Mecanismo por trás de `@property`

Descritores são objetos que definem `__get__`, `__set__` e/ou `__delete__`.
`@property` é um descritor embutido.

```python
from typing import Any

class CampoPositivo:
    """Descritor reutilizável para validar campos numéricos positivos."""

    def __set_name__(self, owner: type, name: str) -> None:
        self._nome_publico = name
        self._nome_privado = f"_{name}"

    def __get__(self, obj: Any, objtype: type | None = None) -> float:
        if obj is None:  # acesso via classe, não instância
            return self  # type: ignore[return-value]
        return getattr(obj, self._nome_privado, 0.0)

    def __set__(self, obj: Any, valor: float) -> None:
        if not isinstance(valor, (int, float)):
            raise TypeError(f"{self._nome_publico} deve ser numérico")
        if valor < 0:
            raise ValueError(f"{self._nome_publico} deve ser positivo, recebido: {valor}")
        setattr(obj, self._nome_privado, float(valor))


class Produto:
    preco = CampoPositivo()
    estoque = CampoPositivo()

    def __init__(self, nome: str, preco: float, estoque: float) -> None:
        self.nome = nome
        self.preco = preco      # dispara CampoPositivo.__set__
        self.estoque = estoque  # dispara CampoPositivo.__set__

# Reutilizável em qualquer classe sem repetir validação
class Servico:
    taxa_hora = CampoPositivo()
    horas_minimas = CampoPositivo()
```

**Quando usar descritores:**
- Validação reutilizável em múltiplas classes
- Atributos com comportamento especial (lazy loading, cache, ORM fields)
- Quando `@property` precisaria ser reescrita várias vezes com a mesma lógica

---

## `__slots__` — Otimização de Memória

```python
import sys

class PontoComDict:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

class PontoComSlots:
    __slots__ = ("x", "y")  # substitui __dict__ por struct C fixo

    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

p1 = PontoComDict(1.0, 2.0)
p2 = PontoComSlots(1.0, 2.0)

print(sys.getsizeof(p1.__dict__))  # ~232 bytes
# p2 não tem __dict__ — redução de ~40-50% na memória por instância
```

**Regras para `__slots__`:**
- Use em classes com MUITAS instâncias (10k+) onde memória importa
- Em herança: cada classe na hierarquia deve declarar seus próprios `__slots__`
- Incompatível com `__dict__` dinâmico e `cached_property` sem ajuste
- `@dataclass` + `__slots__=True` (Python 3.10+): `@dataclass(slots=True)`
