# 03 — Herança, Composição e Mixins

## A Regra Fundamental

> "Herança = É UM. Composição = TEM UM. Quando em dúvida, use composição."

| Critério | Herança | Composição |
|----------|---------|------------|
| Relação | "é um" (`Dog` é um `Animal`) | "tem um" (`Carro` tem um `Motor`) |
| Acoplamento | Forte — subclasse depende da superclasse | Fraco — componentes são intercambiáveis |
| Flexibilidade em runtime | Estática | Dinâmica — pode trocar componentes |
| Testabilidade | Mais difícil | Mais fácil (mock dos componentes) |
| Profundidade máxima recomendada | 2–3 níveis | Ilimitado |

---

## Herança — Quando É Correto Usar

```python
from abc import ABC, abstractmethod

class Forma(ABC):
    def __init__(self, cor: str = "preto") -> None:
        self.cor = cor

    @abstractmethod
    def area(self) -> float: ...

    @abstractmethod
    def perimetro(self) -> float: ...

    def descrever(self) -> str:
        return f"{type(self).__name__}: área={self.area():.2f}, cor={self.cor}"

class Circulo(Forma):
    def __init__(self, raio: float, cor: str = "preto") -> None:
        super().__init__(cor)
        self.raio = raio

    def area(self) -> float:
        import math
        return math.pi * self.raio ** 2

    def perimetro(self) -> float:
        import math
        return 2 * math.pi * self.raio

class Retangulo(Forma):
    def __init__(self, largura: float, altura: float, cor: str = "preto") -> None:
        super().__init__(cor)
        self.largura = largura
        self.altura = altura

    def area(self) -> float:
        return self.largura * self.altura

    def perimetro(self) -> float:
        return 2 * (self.largura + self.altura)
```

---

## Composição — Preferida para Comportamentos Combinados

```python
from dataclasses import dataclass, field
from typing import Protocol

class Motor(Protocol):
    def ligar(self) -> str: ...
    def potencia_cv(self) -> int: ...

@dataclass
class MotorEletrico:
    _potencia: int = 150

    def ligar(self) -> str:
        return "Motor elétrico silencioso"

    def potencia_cv(self) -> int:
        return self._potencia

@dataclass
class MotorCombustao:
    _cilindros: int = 4
    _potencia: int = 120

    def ligar(self) -> str:
        return f"Motor {self._cilindros}cil rugindo"

    def potencia_cv(self) -> int:
        return self._potencia

@dataclass
class Carro:
    modelo: str
    motor: Motor  # composição: recebe qualquer Motor compatível

    def ligar(self) -> str:
        return f"{self.modelo}: {self.motor.ligar()}"

# Flexibilidade total sem alterar a classe Carro
tesla = Carro("Model S", MotorEletrico(300))
civic = Carro("Civic", MotorCombustao(4, 158))
```

---

## Mixins — Herança para Comportamento Reutilizável

Mixins são classes projetadas **exclusivamente** para adicionar comportamento.
Nunca devem ser instanciadas diretamente e não têm estado próprio significativo.

```python
from typing import Any

class ReprMixin:
    """Adiciona __repr__ automático baseado nos atributos da instância."""

    def __repr__(self) -> str:
        attrs = ", ".join(
            f"{k}={v!r}"
            for k, v in vars(self).items()
            if not k.startswith("_")
        )
        return f"{type(self).__name__}({attrs})"

class ComparaMixin:
    """Adiciona comparação por um campo específico."""

    _campo_comparacao: str = "id"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        return getattr(self, self._campo_comparacao) == getattr(other, self._campo_comparacao)

    def __hash__(self) -> int:
        return hash(getattr(self, self._campo_comparacao))

class SerializaMixin:
    """Adiciona serialização para dict."""

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in vars(self).items() if not k.startswith("_")}

# Composição via herança múltipla de mixins
class Usuario(ReprMixin, ComparaMixin, SerializaMixin):
    _campo_comparacao = "email"

    def __init__(self, nome: str, email: str) -> None:
        self.nome = nome
        self.email = email

u = Usuario("Ana", "ana@example.com")
print(repr(u))          # Usuario(nome='Ana', email='ana@example.com')
print(u.to_dict())      # {'nome': 'Ana', 'email': 'ana@example.com'}
```

**Convenção de nomenclatura:** termine mixins com `Mixin` ou `able` (ex: `Serializable`).
**Posição na herança:** mixins vêm antes da classe base principal → `class Filho(Mixin1, Mixin2, BaseReal)`

---

## Herança Múltipla — Uso Correto com `super()`

```python
class LogMixin:
    def salvar(self) -> None:
        print(f"LOG: salvando {type(self).__name__}")
        super().salvar()  # type: ignore[misc]  — cooperativo!

class ValidaMixin:
    def salvar(self) -> None:
        print("VALIDA: verificando dados")
        super().salvar()  # type: ignore[misc]

class BasePersistencia:
    def salvar(self) -> None:
        print("DB: persistindo no banco")

class Entidade(LogMixin, ValidaMixin, BasePersistencia):
    pass

e = Entidade()
e.salvar()
# LOG: salvando Entidade
# VALIDA: verificando dados
# DB: persistindo no banco

# MRO: Entidade → LogMixin → ValidaMixin → BasePersistencia → object
print(Entidade.__mro__)
```

**Regra crítica:** em herança múltipla, SEMPRE use `super()` em todos os níveis da cadeia,
mesmo quando aparentemente não há nada para delegar.

---

## Violações do Princípio de Liskov — O Que Evitar

```python
# ❌ Liskov Violation — Retangulo não pode ser substituído por Quadrado
class Retangulo:
    def __init__(self, largura: float, altura: float) -> None:
        self._largura = largura
        self._altura = altura

    @property
    def largura(self) -> float: return self._largura
    @largura.setter
    def largura(self, v: float) -> None: self._largura = v

    @property
    def altura(self) -> float: return self._altura
    @altura.setter
    def altura(self, v: float) -> None: self._altura = v

class Quadrado(Retangulo):  # ❌ Quadrado NÃO é um Retangulo substituível
    @Retangulo.largura.setter
    def largura(self, v: float) -> None:
        self._largura = v
        self._altura = v  # viola expectativa do caller!

# ✅ Solução: hierarquia separada
from abc import ABC, abstractmethod

class Forma(ABC):
    @abstractmethod
    def area(self) -> float: ...

class Retangulo(Forma):
    def __init__(self, largura: float, altura: float) -> None:
        self.largura = largura
        self.altura = altura
    def area(self) -> float:
        return self.largura * self.altura

class Quadrado(Forma):
    def __init__(self, lado: float) -> None:
        self.lado = lado
    def area(self) -> float:
        return self.lado ** 2
```
