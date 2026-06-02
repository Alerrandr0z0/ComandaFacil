# 01 — Fundamentos de Classes em Python

## Ciclo de Vida de um Objeto

### `__new__` vs `__init__`

```python
class Singleton:
    _instance: "Singleton | None" = None

    def __new__(cls) -> "Singleton":
        # __new__ CRIA o objeto — chamado antes de __init__
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        # __init__ INICIALIZA o objeto já criado
        # Cuidado: __init__ é chamado toda vez que Singleton() é invocado
        pass
```

**Regra:** `__new__` é raramente necessário. Use apenas para: Singleton, objetos imutáveis
(subclasses de `int`, `str`, `tuple`), ou controle de instanciação via metaclasse.

---

## Atributos de Instância vs Atributos de Classe

```python
from typing import ClassVar

class Funcionario:
    # Atributo de CLASSE — compartilhado por todas as instâncias
    empresa: ClassVar[str] = "ACME Corp"
    _total: ClassVar[int] = 0

    def __init__(self, nome: str, salario: float) -> None:
        # Atributos de INSTÂNCIA — únicos por objeto
        self.nome: str = nome
        self._salario: float = salario  # protegido por convenção
        Funcionario._total += 1

    @classmethod
    def total_contratados(cls) -> int:
        return cls._total

    @staticmethod
    def validar_salario(valor: float) -> bool:
        return valor > 0
```

**Armadilha clássica com mutáveis:**
```python
# ❌ ERRADO — lista compartilhada entre todas as instâncias!
class Time:
    jogadores = []  # atributo de classe mutável

    def adicionar(self, jogador: str) -> None:
        self.jogadores.append(jogador)  # modifica a lista da CLASSE

# ✅ CORRETO
class Time:
    def __init__(self) -> None:
        self.jogadores: list[str] = []  # atributo de instância
```

---

## `@classmethod` vs `@staticmethod` vs método de instância

```python
from datetime import date

class Pessoa:
    def __init__(self, nome: str, ano_nascimento: int) -> None:
        self.nome = nome
        self.ano_nascimento = ano_nascimento

    # Método de instância — acessa self (a instância)
    def idade(self) -> int:
        return date.today().year - self.ano_nascimento

    # @classmethod — acessa cls (a classe); usado como factory method
    @classmethod
    def de_string(cls, dados: str) -> "Pessoa":
        nome, ano = dados.split(",")
        return cls(nome.strip(), int(ano.strip()))

    # @staticmethod — não acessa nem self nem cls; é uma função no namespace da classe
    @staticmethod
    def eh_maior_de_idade(idade: int) -> bool:
        return idade >= 18

# Uso
p = Pessoa.de_string("Ana, 1990")  # factory method
print(Pessoa.eh_maior_de_idade(20))  # True
```

**Quando usar cada um:**
- Método de instância: precisa acessar/modificar o estado do objeto → use `self`
- `@classmethod`: factory methods, acesso a atributos de classe → use `cls`
- `@staticmethod`: lógica utilitária relacionada à classe, mas sem acesso a estado → sem `self`/`cls`

---

## `__post_init__` — Validação em Dataclasses

```python
from dataclasses import dataclass
from datetime import date

@dataclass
class Contrato:
    cliente: str
    valor: float
    inicio: date
    fim: date

    def __post_init__(self) -> None:
        if self.valor <= 0:
            raise ValueError(f"Valor inválido: {self.valor}")
        if self.fim <= self.inicio:
            raise ValueError("Data de fim deve ser após a de início")
        # Normalização
        self.cliente = self.cliente.strip().title()
```

---

## Herança Básica e `super()`

```python
class Veiculo:
    def __init__(self, marca: str, ano: int) -> None:
        self.marca = marca
        self.ano = ano

    def descrever(self) -> str:
        return f"{self.marca} ({self.ano})"

class Carro(Veiculo):
    def __init__(self, marca: str, ano: int, portas: int) -> None:
        super().__init__(marca, ano)  # sempre chame super().__init__()
        self.portas = portas

    def descrever(self) -> str:
        base = super().descrever()
        return f"{base}, {self.portas} portas"
```

**Regra:** sempre use `super()` sem argumentos (forma cooperativa). Nunca `ParentClass.__init__(self, ...)`.

---

## MRO — Method Resolution Order

```python
class A:
    def metodo(self) -> str:
        return "A"

class B(A):
    def metodo(self) -> str:
        return f"B -> {super().metodo()}"

class C(A):
    def metodo(self) -> str:
        return f"C -> {super().metodo()}"

class D(B, C):
    pass

d = D()
print(d.metodo())       # "B -> C -> A"
print(D.__mro__)        # (D, B, C, A, object)
```

Python usa o algoritmo **C3 Linearization**. Inspecione sempre com `ClassName.__mro__`
ao usar herança múltipla.
