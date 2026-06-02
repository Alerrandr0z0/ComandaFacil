# 09 — Anti-Patterns OOP: O Que Evitar e Por Quê

## Anti-Pattern 1: God Object / God Class

```python
# ❌ Classe que faz tudo — viola SRP, impossível de testar
class SistemaVendas:
    def criar_usuario(self): ...
    def autenticar(self): ...
    def criar_produto(self): ...
    def calcular_preco(self): ...
    def processar_pagamento(self): ...
    def enviar_email(self): ...
    def gerar_relatorio(self): ...
    def conectar_banco(self): ...

# ✅ Separar em classes com responsabilidade única
class AutenticacaoService: ...
class ProdutoService: ...
class PagamentoService: ...
class NotificacaoService: ...
```

**Sintoma:** classe com mais de ~200 linhas ou que você descreve com "e" (faz X **e** Y **e** Z).

---

## Anti-Pattern 2: Herança para Reuso de Código

```python
# ❌ Herdar só para reutilizar métodos — não há relação "é um"
class Utilitarios:
    def formatar_data(self, d): ...
    def calcular_desconto(self, preco, pct): ...

class Pedido(Utilitarios):  # Pedido NÃO "é um" Utilitario
    pass

# ✅ Composição ou funções utilitárias no módulo
def formatar_data(d): ...
def calcular_desconto(preco: float, percentual: float) -> float:
    return preco * (1 - percentual / 100)

class Pedido:
    def total_com_desconto(self, percentual: float) -> float:
        return calcular_desconto(self.valor, percentual)
```

---

## Anti-Pattern 3: Getter/Setter Java-Style

```python
# ❌ Verboso e não-pythônico
class Produto:
    def __init__(self, nome: str) -> None:
        self._nome = nome

    def get_nome(self) -> str:
        return self._nome

    def set_nome(self, nome: str) -> None:
        self._nome = nome

# ✅ Use atributo público ou @property quando necessário
class Produto:
    def __init__(self, nome: str) -> None:
        self.nome = nome  # direto, se não há validação

class ProdutoComValidacao:
    def __init__(self, nome: str) -> None:
        self._nome = ""
        self.nome = nome  # dispara o setter

    @property
    def nome(self) -> str:
        return self._nome

    @nome.setter
    def nome(self, valor: str) -> None:
        if not valor.strip():
            raise ValueError("Nome não pode ser vazio")
        self._nome = valor.strip().title()
```

---

## Anti-Pattern 4: Atributos Mutáveis como Default

```python
# ❌ Lista compartilhada entre TODAS as instâncias
class Time:
    jogadores = []  # atributo de CLASSE, não de instância!

    def adicionar(self, j: str) -> None:
        self.jogadores.append(j)  # modifica a classe!

t1 = Time()
t2 = Time()
t1.adicionar("Ana")
print(t2.jogadores)  # ['Ana'] — BUG! t2 também tem 'Ana'

# ✅ Inicializar no __init__ ou usar field(default_factory=...)
class Time:
    def __init__(self) -> None:
        self.jogadores: list[str] = []  # cada instância tem sua lista

# Com @dataclass:
from dataclasses import dataclass, field

@dataclass
class TimeDataclass:
    jogadores: list[str] = field(default_factory=list)
```

---

## Anti-Pattern 5: Hierarquia de Herança Profunda

```python
# ❌ Hierarquia de 5+ níveis — refactoring pesadelo
class A: ...
class B(A): ...
class C(B): ...
class D(C): ...
class E(D): ...  # Qual método exatamente está sendo chamado?

# ✅ Máximo 2-3 níveis, prefira composição/mixins
class Base: ...
class Concreto(Base): ...  # 2 níveis está ótimo
```

---

## Anti-Pattern 6: Ignorar `NotImplemented` em Operadores

```python
# ❌ Lança TypeError genérico
class Valor:
    def __eq__(self, other: object) -> bool:
        return self._v == other._v  # AttributeError se other não tiver _v!

# ✅ Retorne NotImplemented para tipos desconhecidos
class Valor:
    def __init__(self, v: int) -> None:
        self._v = v

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Valor):
            return NotImplemented  # permite que Python tente o outro lado
        return self._v == other._v

    def __hash__(self) -> int:
        return hash(self._v)  # OBRIGATÓRIO se __eq__ definido
```

---

## Anti-Pattern 7: `type(x) == Classe` em vez de `isinstance`

```python
# ❌ Não considera subclasses, mais lento
def processar(obj):
    if type(obj) == str:  # quebra com subclasses de str
        return obj.upper()

# ✅ isinstance considera subclasses
def processar(obj: object) -> str:
    if isinstance(obj, str):
        return obj.upper()
    return str(obj)

# ✅✅ Duck typing com Protocol — ainda melhor
from typing import Protocol

class Formatavel(Protocol):
    def upper(self) -> str: ...

def processar_proto(obj: Formatavel) -> str:
    return obj.upper()
```

---

## Anti-Pattern 8: Classes Sem `__repr__`

```python
# ❌ Debugging impossível
class Pedido:
    def __init__(self, id: int, valor: float) -> None:
        self.id = id
        self.valor = valor
# repr padrão: <__main__.Pedido object at 0x7f3e4c>  — inútil!

# ✅ Sempre implemente __repr__
class Pedido:
    def __init__(self, id: int, valor: float) -> None:
        self.id = id
        self.valor = valor

    def __repr__(self) -> str:
        return f"Pedido(id={self.id!r}, valor={self.valor!r})"
# repr: Pedido(id=42, valor=150.0)
```

---

## Anti-Pattern 9: Usar `__init__` como Factory

```python
# ❌ __init__ com lógica condicional complexa de criação
class Conexao:
    def __init__(self, tipo: str, **kwargs) -> None:
        if tipo == "postgres":
            self._conn = self._criar_postgres(**kwargs)
        elif tipo == "mysql":
            self._conn = self._criar_mysql(**kwargs)
        # ...

# ✅ Factory methods ou função fábrica
class Conexao:
    def __init__(self, conn_obj) -> None:
        self._conn = conn_obj

    @classmethod
    def postgres(cls, host: str, porta: int) -> "Conexao":
        return cls(criar_postgres(host, porta))

    @classmethod
    def mysql(cls, dsn: str) -> "Conexao":
        return cls(criar_mysql(dsn))
```

---

## Anti-Pattern 10: Pydantic Everywhere

```python
# ❌ Pydantic em objetos de domínio interno (lento, desnecessário)
from pydantic import BaseModel

class PontoInterno(BaseModel):  # usado internamente, nunca serializado
    x: float
    y: float

# Usado em hot path com milhares de instâncias → impacto significativo!

# ✅ @dataclass para objetos internos
from dataclasses import dataclass

@dataclass(frozen=True)
class PontoInterno:
    x: float
    y: float

# Pydantic apenas nas bordas do sistema (entrada de API, configs, etc.)
```

---

## Regra de Ouro Anti-Patterns

> Se ao descrever sua classe você usa "E" mais de uma vez, ela viola SRP.
> Se sua hierarquia tem mais de 3 níveis, prefira composição.
> Se você tem getters/setters, use `@property`.
> Se esqueceu `__repr__`, você vai se arrepender no primeiro bug de produção.
