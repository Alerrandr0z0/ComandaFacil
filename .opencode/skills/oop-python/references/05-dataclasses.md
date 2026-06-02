# 05 — Dataclasses: Guia Completo

## Por Que Dataclasses?

```python
# ❌ Classe manual verbosa (pre-dataclass)
class PontoManual:
    def __init__(self, x: float, y: float, z: float = 0.0) -> None:
        self.x = x
        self.y = y
        self.z = z

    def __repr__(self) -> str:
        return f"PontoManual(x={self.x}, y={self.y}, z={self.z})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PontoManual):
            return NotImplemented
        return (self.x, self.y, self.z) == (other.x, other.y, other.z)

# ✅ Dataclass equivalente — muito menos código, mais correto
from dataclasses import dataclass

@dataclass
class Ponto:
    x: float
    y: float
    z: float = 0.0
```

---

## Parâmetros do Decorator `@dataclass`

```python
from dataclasses import dataclass

@dataclass(
    init=True,       # gera __init__ (padrão: True)
    repr=True,       # gera __repr__ (padrão: True)
    eq=True,         # gera __eq__ e __hash__ (padrão: True)
    order=False,     # gera __lt__, __le__, __gt__, __ge__ (padrão: False)
    frozen=False,    # torna imutável — gera __setattr__/__delattr__ que levantam FrozenInstanceError
    unsafe_hash=False,  # força __hash__ mesmo com eq=True e frozen=False
    slots=False,     # gera __slots__ automaticamente (Python 3.10+)
    kw_only=False,   # todos os campos são keyword-only (Python 3.10+)
    match_args=True, # gera __match_args__ para pattern matching (Python 3.10+)
)
class Configuracao:
    host: str
    porta: int = 8080
```

---

## `field()` — Controle Granular

```python
from dataclasses import dataclass, field
from typing import ClassVar

@dataclass
class Tarefa:
    # ClassVar — não é campo da instância, não aparece em __init__
    _contador: ClassVar[int] = 0

    titulo: str
    prioridade: int = field(default=5, metadata={"min": 1, "max": 10})

    # default_factory para mutáveis — OBRIGATÓRIO para listas/dicts
    tags: list[str] = field(default_factory=list)
    metadados: dict[str, object] = field(default_factory=dict)

    # campo excluído do __repr__
    senha_interna: str = field(default="", repr=False)

    # campo excluído do __init__ — calculado em __post_init__
    id: int = field(init=False)

    # campo excluído de comparação __eq__
    criado_por: str = field(default="sistema", compare=False)

    def __post_init__(self) -> None:
        Tarefa._contador += 1
        self.id = Tarefa._contador
        if not 1 <= self.prioridade <= 10:
            raise ValueError(f"Prioridade deve ser 1-10, recebido: {self.prioridade}")
```

---

## Value Objects com `frozen=True`

```python
from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True, order=True)
class Dinheiro:
    """Value Object imutável para representar valores monetários."""
    valor: Decimal
    moeda: str = "BRL"

    def __post_init__(self) -> None:
        if self.valor < 0:
            raise ValueError("Valor não pode ser negativo")
        # frozen=True não impede __post_init__, mas impede atribuição posterior
        # Para coerção de tipo em frozen:
        object.__setattr__(self, "valor", Decimal(str(self.valor)))
        object.__setattr__(self, "moeda", self.moeda.upper())

    def __add__(self, other: "Dinheiro") -> "Dinheiro":
        if self.moeda != other.moeda:
            raise ValueError(f"Moedas incompatíveis: {self.moeda} vs {other.moeda}")
        return Dinheiro(self.valor + other.valor, self.moeda)

    def __mul__(self, fator: Decimal | int | float) -> "Dinheiro":
        return Dinheiro(self.valor * Decimal(str(fator)), self.moeda)

    def formatar(self) -> str:
        return f"{self.moeda} {self.valor:.2f}"

r1 = Dinheiro(100)
r2 = Dinheiro(50)
total = r1 + r2  # Dinheiro(valor=Decimal('150'), moeda='BRL')
```

---

## Herança em Dataclasses

```python
from dataclasses import dataclass

@dataclass
class Entidade:
    id: int
    versao: int = 1

@dataclass
class Usuario(Entidade):
    nome: str = ""  # campos sem default devem vir após campos com default da pai
    email: str = ""

# OU use kw_only para evitar o problema de ordem:
@dataclass(kw_only=True)
class Produto(Entidade):
    nome: str       # agora pode vir sem default, pois kw_only=True
    preco: float
```

**Regra:** em herança de dataclasses, campos sem default não podem seguir campos com default.
Use `kw_only=True` (Python 3.10+) para resolver.

---

## `__post_init__` com Herança

```python
from dataclasses import dataclass

@dataclass
class Animal:
    nome: str
    peso_kg: float

    def __post_init__(self) -> None:
        self.nome = self.nome.strip().title()

@dataclass
class Cachorro(Animal):
    raca: str = "SRD"

    def __post_init__(self) -> None:
        super().__post_init__()  # SEMPRE chame o pai!
        self.raca = self.raca.title()
```

---

## `dataclasses.asdict` e `astuple`

```python
from dataclasses import dataclass, asdict, astuple

@dataclass
class Endereco:
    rua: str
    cidade: str
    estado: str

@dataclass
class Pessoa:
    nome: str
    endereco: Endereco

p = Pessoa("Ana", Endereco("Rua A", "SP", "SP"))

# Conversão recursiva para dict
print(asdict(p))
# {'nome': 'Ana', 'endereco': {'rua': 'Rua A', 'cidade': 'SP', 'estado': 'SP'}}

# Conversão recursiva para tupla
print(astuple(p))
# ('Ana', ('Rua A', 'SP', 'SP'))
```

---

## `dataclasses.replace` — Atualização de Objetos Imutáveis

```python
from dataclasses import dataclass, replace

@dataclass(frozen=True)
class Configuracao:
    host: str = "localhost"
    porta: int = 8080
    debug: bool = False

config_dev = Configuracao(host="localhost", debug=True)
config_prod = replace(config_dev, host="api.exemplo.com", debug=False)

# config_dev inalterado, config_prod é novo objeto
```

---

## Dataclass vs Pydantic — Quando Usar Cada Um

| Critério | `@dataclass` | Pydantic `BaseModel` |
|----------|-------------|----------------------|
| Validação em runtime | Apenas em `__post_init__` | Automática por tipo |
| Performance | ~5-10x mais rápido | Mais lento |
| Serialização JSON | Manual (`asdict` + `json`) | `.model_dump()`, `.model_dump_json()` |
| Validação de tipos | Não (apenas type hints) | Sim (coerce/validate) |
| Ideal para | Lógica interna, value objects | API boundaries, configs, input validation |
| Dependência externa | Nenhuma (stdlib) | Requer `pydantic` |

```python
# Use @dataclass para objetos de domínio interno
@dataclass(frozen=True)
class Coordenada:
    lat: float
    lon: float

# Use Pydantic para entrada de API / validação externa
from pydantic import BaseModel, field_validator

class CriarUsuarioRequest(BaseModel):
    nome: str
    email: str
    idade: int

    @field_validator("email")
    @classmethod
    def validar_email(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("Email inválido")
        return v.lower()
```
