# 10 — Checklist de Qualidade OOP Python

Use este checklist ao revisar ou criar código OOP Python.

---

## ✅ Checklist por Classe

### Design e Responsabilidade
- [ ] A classe tem **uma única responsabilidade** — consigo descrevê-la em 1 frase sem usar "e"?
- [ ] O nome da classe é um **substantivo** (não verbo) que reflete o que ela representa?
- [ ] A classe não tem mais de ~200 linhas (excluindo docstrings)?
- [ ] Se a classe faz mais de 5 coisas distintas, considerei dividi-la?

### Herança e Composição
- [ ] A herança representa uma relação genuína "é um"?
- [ ] A hierarquia tem no máximo 3 níveis?
- [ ] Preferi composição quando o relacionamento é "tem um"?
- [ ] Cada subclasse pode **substituir** a superclasse sem quebrar comportamento (Liskov)?
- [ ] Mixins são usados apenas para comportamento (sem estado significativo)?
- [ ] Usei `super().__init__()` em todas as subclasses?

### Encapsulamento
- [ ] Atributos públicos representam a interface real da classe?
- [ ] Usei `_prefixo` para atributos internos?
- [ ] Usei `@property` em vez de getters/setters Java-style?
- [ ] Validações estão nos setters/`__post_init__`, não espalhadas pelo código?

### Tipo de Classe Adequado
- [ ] Se a classe armazena principalmente dados, considerei `@dataclass`?
- [ ] Se é um contrato sem herança obrigatória, usei `Protocol`?
- [ ] Se força implementação em subclasses, usei `ABC`?
- [ ] Se precisa de memória otimizada (10k+ instâncias), usei `__slots__`?

### Métodos Essenciais
- [ ] `__repr__` implementado? (sempre obrigatório)
- [ ] `__str__` implementado se a representação "para usuário" difere do repr?
- [ ] Se `__eq__` definido, `__hash__` também foi definido?
- [ ] Operadores retornam `NotImplemented` para tipos desconhecidos?

### Type Hints
- [ ] Todos os parâmetros de `__init__` têm anotações?
- [ ] Todos os métodos públicos têm anotações de retorno?
- [ ] Atributos de instância são declarados no `__init__` com anotação?
- [ ] `ClassVar` usado para atributos de classe?
- [ ] `Final` usado para constantes?

### Qualidade Geral
- [ ] Cada método público tem docstring?
- [ ] Não há lógica de negócio em `__init__` (use `__post_init__` ou factory)?
- [ ] Dependências são injetadas via `__init__` (não instanciadas dentro)?
- [ ] A classe é testável unitariamente (sem dependências externas hard-coded)?

---

## ✅ Checklist por Hierarquia

- [ ] Existe uma ABC ou Protocol definindo o contrato?
- [ ] Todas as subclasses implementam os métodos abstratos?
- [ ] Nenhuma subclasse viola o contrato da superclasse?
- [ ] O MRO foi verificado com `ClassName.__mro__`?
- [ ] Herança múltipla usa `super()` de forma cooperativa em todos os níveis?

---

## ✅ Checklist de Testabilidade

- [ ] Classes concretas dependem de abstrações (Protocol/ABC), não de implementações?
- [ ] É possível injetar dependências mockadas/falsas no `__init__`?
- [ ] Lógica pura (sem I/O) está separada da lógica com efeitos colaterais?
- [ ] Existe ao menos um teste para cada método público?

---

## ✅ Checklist de Performance

- [ ] Em hot paths com 10k+ instâncias, `__slots__` foi considerado?
- [ ] `@cached_property` usado para propriedades computacionalmente caras?
- [ ] Objetos imutáveis usam `frozen=True` (permitindo hash e uso em sets)?
- [ ] Pydantic não está sendo usado em objetos internos (apenas nas bordas)?

---

## Pontuação Rápida

Ao revisar uma classe, conte as marcações:
- **>90%** ✅ → código de produção, bem estruturado
- **70-90%** ✅ → bom, com alguns pontos a melhorar
- **50-70%** ✅ → necessita refatoração significativa
- **<50%** ✅ → considere reescrever com os padrões corretos

---

## Template Mínimo de Classe Python Moderno

```python
from __future__ import annotations  # permite forward references em type hints

from typing import ClassVar, Final, TYPE_CHECKING

if TYPE_CHECKING:
    pass  # imports apenas para type checking — evita circulares

class MinhaClasse:
    """
    Descrição em uma linha do que a classe representa.

    Attributes:
        atributo: Descrição do atributo público.
    """

    CONSTANTE: Final[str] = "valor"
    _contagem: ClassVar[int] = 0

    def __init__(self, valor: str) -> None:
        self._valor: str = valor
        MinhaClasse._contagem += 1

    @property
    def valor(self) -> str:
        """Descrição da propriedade."""
        return self._valor

    @valor.setter
    def valor(self, novo: str) -> None:
        if not novo:
            raise ValueError("Valor não pode ser vazio")
        self._valor = novo

    def __repr__(self) -> str:
        return f"{type(self).__name__}(valor={self._valor!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MinhaClasse):
            return NotImplemented
        return self._valor == other._valor

    def __hash__(self) -> int:
        return hash(self._valor)

    @classmethod
    def total(cls) -> int:
        """Retorna o total de instâncias criadas."""
        return cls._contagem
```
