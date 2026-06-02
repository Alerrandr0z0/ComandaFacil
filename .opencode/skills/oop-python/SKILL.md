---
name: oop-python
description: >
  Guia completo e rigoroso de OOP (Programação Orientada a Objetos) em Python moderno.
  Use este skill SEMPRE que o usuário pedir ajuda com: classes Python, herança, encapsulamento,
  polimorfismo, abstração, design patterns, SOLID, dataclasses, Protocol, ABC, type hints em classes,
  dunder/magic methods, metaclasses, descritores, composição vs herança, refatoração de código OOP,
  arquitetura orientada a objetos, ou qualquer dúvida sobre como estruturar código Python com classes.
  Também acionar para: "como criar uma classe", "o que é herança em Python", "como usar @property",
  "qual a diferença entre ABC e Protocol", "como aplicar SOLID no Python", "como evitar herança profunda",
  "como usar dataclass", e qualquer pedido de revisão ou melhoria de código Python orientado a objetos.
---

# Skill: OOP em Python — Guia Rigoroso e Moderno

## Visão Geral

Este skill cobre OOP em Python de forma completa: dos fundamentos aos padrões avançados de produção.
Organizado em camadas para consulta rápida — leia a seção relevante, não o documento inteiro.

**Referências detalhadas por tema:**
- `references/01-fundamentos.md` — Classes, instâncias, `__init__`, `__new__`, atributos
- `references/02-encapsulamento.md` — `_`, `__`, `@property`, descritores
- `references/03-heranca-composicao.md` — Herança, MRO, composição, mixins
- `references/04-abstracoes.md` — ABC, Protocol, duck typing, interfaces
- `references/05-dataclasses.md` — `@dataclass`, `frozen=True`, `field()`, Pydantic
- `references/06-solid-patterns.md` — SOLID, GoF patterns, Dependency Injection
- `references/07-avancado.md` — Metaclasses, descritores, `__slots__`, dunder methods
- `references/08-type-hints.md` — Anotações, mypy, generics em classes
- `references/09-antipatterns.md` — O que evitar e por quê
- `references/10-checklist.md` — Checklist de qualidade para revisão de código OOP

---

## Guia de Decisão Rápida

### "Que ferramenta OOP devo usar?"

```
Preciso modelar DADOS com campos fixos?
  └─► @dataclass (ou Pydantic se precisar de validação/serialização)

Preciso de um CONTRATO sem herança obrigatória (duck typing moderno)?
  └─► Protocol (typing.Protocol) — preferido no Python moderno

Preciso forçar implementação de métodos nas subclasses?
  └─► ABC (abc.ABC + @abstractmethod)

Preciso de lógica de negócio complexa + estado mutável?
  └─► Classe regular com @property, encapsulamento adequado

Preciso de COMPORTAMENTO reutilizável entre classes não relacionadas?
  └─► Mixin (herança múltipla restrita a comportamento, sem estado)

Preciso de MEMÓRIA OTIMIZADA para milhares de instâncias?
  └─► __slots__

Preciso de CONTROLE NA CRIAÇÃO DA CLASSE (não da instância)?
  └─► Metaclasse (use com extrema moderação)
```

---

## Os 5 Pilares Modernos do OOP Python

### 1. Encapsulamento real (não só sintático)
```python
class ContaBancaria:
    def __init__(self, saldo_inicial: float = 0.0) -> None:
        self._saldo: float = saldo_inicial  # convenção: protegido
        self.__historico: list[float] = []  # name-mangled: privado real

    @property
    def saldo(self) -> float:
        return self._saldo

    def depositar(self, valor: float) -> None:
        if valor <= 0:
            raise ValueError(f"Valor deve ser positivo, recebido: {valor}")
        self._saldo += valor
        self.__historico.append(valor)
```
**Regra:** use `_` por convenção; `__` apenas quando name-mangling é necessário.
`@property` é o modo pythônico de controlar acesso — evite getters/setters Java-style.

### 2. Composição sobre Herança
```python
# ❌ Hierarquia frágil
class Animal:
    def mover(self): ...
class Ave(Animal):
    def voar(self): ...
class AveAquatica(Ave):  # E se um pinguim não voa?
    def nadar(self): ...

# ✅ Composição flexível
from dataclasses import dataclass, field

@dataclass
class CapacidadeVoo:
    velocidade_max_kmh: float
    def voar(self) -> str:
        return f"Voando a {self.velocidade_max_kmh} km/h"

@dataclass
class CapacidadeNatacao:
    profundidade_max_m: float
    def nadar(self) -> str:
        return f"Nadando até {self.profundidade_max_m}m"

@dataclass
class Pato:
    voo: CapacidadeVoo = field(default_factory=lambda: CapacidadeVoo(50))
    natacao: CapacidadeNatacao = field(default_factory=lambda: CapacidadeNatacao(5))
```
**Regra:** herança = "é um". Composição = "tem um". Quando em dúvida, componha.

### 3. Protocol para contratos modernos
```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Notificavel(Protocol):
    def enviar(self, mensagem: str) -> bool: ...
    def status(self) -> str: ...

# Qualquer classe com esses métodos satisfaz o protocolo — sem herança
class EmailService:
    def enviar(self, mensagem: str) -> bool:
        print(f"Email: {mensagem}")
        return True
    def status(self) -> str:
        return "online"

def notificar_usuario(servico: Notificavel, msg: str) -> None:
    servico.enviar(msg)  # Funciona com qualquer implementação
```
**Regra:** prefira `Protocol` para novas abstrações; `ABC` quando você controla toda a hierarquia.

### 4. @dataclass para objetos de valor
```python
from dataclasses import dataclass, field
from datetime import datetime

@dataclass(frozen=True)  # imutável — ideal para value objects
class Pedido:
    id: int
    cliente: str
    valor: float
    criado_em: datetime = field(default_factory=datetime.now)
    itens: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.valor < 0:
            raise ValueError("Valor do pedido não pode ser negativo")
```
**Regra:** `@dataclass` elimina ~70% dos casos em que se usava classes verbosas só para dados.
Use `frozen=True` para value objects imutáveis.

### 5. Type hints completos em todas as classes
```python
from typing import ClassVar, Final
from collections.abc import Iterator

class Contador:
    _total_instancias: ClassVar[int] = 0  # atributo de classe tipado
    LIMITE: Final[int] = 100              # constante de classe

    def __init__(self, inicio: int = 0) -> None:
        self._valor: int = inicio
        Contador._total_instancias += 1

    def __iter__(self) -> Iterator[int]:
        return iter(range(self._valor, self.LIMITE))

    @classmethod
    def total(cls) -> int:
        return cls._total_instancias
```

---

## SOLID em Python — Resumo Executivo

| Princípio | O que significa | Como aplicar em Python |
|-----------|-----------------|------------------------|
| **S** — Single Responsibility | Uma classe, uma razão para mudar | Se você usa "e" para descrever a classe, divida-a |
| **O** — Open/Closed | Aberta para extensão, fechada para modificação | Use `Protocol`/`ABC` + polimorfismo |
| **L** — Liskov Substitution | Subclasses devem ser substituíveis pela superclasse | Nunca enfraqueça contratos em subclasses |
| **I** — Interface Segregation | Interfaces pequenas e específicas | Vários `Protocol`s pequenos > um `ABC` gigante |
| **D** — Dependency Inversion | Dependa de abstrações, não de implementações | Injete dependências via `__init__` |

---

## Dunder Methods Essenciais

```python
class Produto:
    def __init__(self, nome: str, preco: float) -> None:
        self.nome = nome
        self.preco = preco

    # Representação legível para desenvolvedores
    def __repr__(self) -> str:
        return f"Produto(nome={self.nome!r}, preco={self.preco})"

    # Representação para usuário final
    def __str__(self) -> str:
        return f"{self.nome} — R$ {self.preco:.2f}"

    # Comparação por igualdade
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Produto):
            return NotImplemented
        return self.nome == other.nome and self.preco == other.preco

    # Necessário para usar em sets/dict keys se __eq__ definido
    def __hash__(self) -> int:
        return hash((self.nome, self.preco))

    # Comparação de ordenação
    def __lt__(self, other: "Produto") -> bool:
        return self.preco < other.preco
```

**Regra crítica:** se você define `__eq__`, defina também `__hash__` (ou `hash=False` em dataclass).

---

## Anti-Patterns Críticos — Evite Sempre

1. **God Class** — classe com 500+ linhas fazendo tudo → divida por responsabilidade
2. **Herança para reuso de código** — use composição ou mixins
3. **Hierarquia profunda (>3 níveis)** — quase sempre indica design errado
4. **Getter/Setter Java-style** (`get_nome()`, `set_nome()`) → use `@property`
5. **`type(x) == SomeClass`** → use `isinstance(x, SomeClass)`
6. **Atributos mutáveis como default em `__init__`** — use `field(default_factory=list)`
7. **Pydantic em todo lugar** — use apenas nas fronteiras do sistema (entrada/saída de API)
8. **Ignorar type hints** — em OOP Python moderno, type hints são obrigatórios

---

## Quando NÃO usar classes

Python não exige OOP. Prefira funções/módulos quando:
- O código não tem estado ou o estado é trivial
- Você tem um grupo de funções utilitárias sem relação entre si
- Uma `namedtuple` ou `TypedDict` resolve o problema

```python
# ❌ Classe desnecessária
class MathUtils:
    @staticmethod
    def somar(a: int, b: int) -> int:
        return a + b

# ✅ Módulo é suficiente
def somar(a: int, b: int) -> int:
    return a + b
```

---

## Fluxo de Trabalho ao Criar uma Classe

1. **Defina a responsabilidade** — escreva uma frase de 1 linha descrevendo a classe
2. **Escolha a ferramenta certa** — use o Guia de Decisão Rápida acima
3. **Esboce a interface pública** — métodos e propriedades que outros código usarão
4. **Adicione type hints** — todos os parâmetros, retornos e atributos de instância
5. **Implemente `__repr__`** — sempre; `__str__` se necessário
6. **Escreva testes** — uma classe sem teste é um bug esperando acontecer
7. **Consulte o checklist** — `references/10-checklist.md`

---

## Leitura Aprofundada

Para detalhes completos com exemplos extensos, consulte os arquivos em `references/`:

- Iniciante/intermediário: comece por `01-fundamentos.md`, `02-encapsulamento.md`, `03-heranca-composicao.md`
- Pronto para produção: `04-abstracoes.md`, `05-dataclasses.md`, `06-solid-patterns.md`
- Avançado: `07-avancado.md`, `08-type-hints.md`
- Revisão de código: `09-antipatterns.md`, `10-checklist.md`
