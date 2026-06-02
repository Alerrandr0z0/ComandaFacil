# 06 — SOLID e Design Patterns em Python

## S — Single Responsibility Principle

```python
# ❌ Classe com múltiplas responsabilidades
class Pedido:
    def calcular_total(self) -> float: ...
    def salvar_no_banco(self) -> None: ...    # responsabilidade de persistência
    def enviar_email_confirmacao(self) -> None: ...  # responsabilidade de notificação
    def gerar_pdf(self) -> bytes: ...         # responsabilidade de geração de relatório

# ✅ Responsabilidades separadas
class Pedido:
    def calcular_total(self) -> float: ...

class PedidoRepository:
    def salvar(self, pedido: "Pedido") -> None: ...

class NotificacaoPedido:
    def enviar_confirmacao(self, pedido: "Pedido") -> None: ...

class RelatorioPedido:
    def gerar_pdf(self, pedido: "Pedido") -> bytes: ...
```

## O — Open/Closed Principle

```python
from typing import Protocol

class DescontoStrategy(Protocol):
    def calcular(self, preco: float) -> float: ...

class SemDesconto:
    def calcular(self, preco: float) -> float:
        return preco

class DescontoPercentual:
    def __init__(self, percentual: float) -> None:
        self.percentual = percentual

    def calcular(self, preco: float) -> float:
        return preco * (1 - self.percentual / 100)

class DescontoFidelidade:
    def __init__(self, pontos: int) -> None:
        self.pontos = pontos

    def calcular(self, preco: float) -> float:
        desconto = min(self.pontos * 0.01, 0.3)  # máx 30%
        return preco * (1 - desconto)

class Carrinho:
    def __init__(self, desconto: DescontoStrategy) -> None:
        self._desconto = desconto
        self._itens: list[float] = []

    def finalizar(self) -> float:
        total = sum(self._itens)
        return self._desconto.calcular(total)

# Adicionar novo tipo de desconto NÃO modifica Carrinho
```

## L — Liskov Substitution Principle

```python
# Subclasse deve poder substituir a superclasse sem quebrar o comportamento

from abc import ABC, abstractmethod

class Notificador(ABC):
    @abstractmethod
    def notificar(self, mensagem: str) -> bool:
        """Retorna True se enviado com sucesso."""
        ...

class EmailNotificador(Notificador):
    def notificar(self, mensagem: str) -> bool:
        # Não pode lançar exceção onde o contrato diz retornar bool
        # Não pode exigir parâmetros extras
        # Não pode retornar tipo diferente
        print(f"Email: {mensagem}")
        return True

class SlackNotificador(Notificador):
    def notificar(self, mensagem: str) -> bool:
        print(f"Slack: {mensagem}")
        return True  # Substituível por qualquer Notificador
```

## I — Interface Segregation Principle

```python
# ❌ Interface gorda — força implementação de métodos não usados
from abc import ABC, abstractmethod

class DispositivoGordo(ABC):
    @abstractmethod
    def imprimir(self) -> None: ...
    @abstractmethod
    def escanear(self) -> None: ...
    @abstractmethod
    def enviar_fax(self) -> None: ...  # nem todo dispositivo faz isso!

# ✅ Interfaces segregadas
class Imprimivel(Protocol):
    def imprimir(self) -> None: ...

class Escaneavel(Protocol):
    def escanear(self) -> None: ...

class Faxeavel(Protocol):
    def enviar_fax(self) -> None: ...

class ImpressoraSimples:  # só implementa o que precisa
    def imprimir(self) -> None:
        print("Imprimindo...")

class MultiFuncional:
    def imprimir(self) -> None: ...
    def escanear(self) -> None: ...
    def enviar_fax(self) -> None: ...
```

## D — Dependency Inversion Principle

```python
from typing import Protocol

class GeradorRelatorio(Protocol):
    def gerar(self, dados: list[dict]) -> bytes: ...

class ServicoEmail(Protocol):
    def enviar(self, para: str, assunto: str, corpo: bytes) -> None: ...

class ProcessadorDados:
    # Depende de abstrações (Protocols), não de implementações concretas
    def __init__(
        self,
        gerador: GeradorRelatorio,
        email: ServicoEmail,
    ) -> None:
        self._gerador = gerador
        self._email = email

    def processar_e_enviar(self, dados: list[dict], destinatario: str) -> None:
        relatorio = self._gerador.gerar(dados)
        self._email.enviar(destinatario, "Relatório", relatorio)
```

---

## Design Patterns GoF em Python

### Strategy Pattern

```python
from typing import Protocol
from dataclasses import dataclass

class OrdenacaoStrategy(Protocol):
    def ordenar(self, dados: list[int]) -> list[int]: ...

class QuickSort:
    def ordenar(self, dados: list[int]) -> list[int]:
        return sorted(dados)  # simplificado

class BubbleSort:
    def ordenar(self, dados: list[int]) -> list[int]:
        d = dados.copy()
        for i in range(len(d)):
            for j in range(len(d) - 1 - i):
                if d[j] > d[j+1]:
                    d[j], d[j+1] = d[j+1], d[j]
        return d

@dataclass
class Sorter:
    strategy: OrdenacaoStrategy

    def processar(self, dados: list[int]) -> list[int]:
        return self.strategy.ordenar(dados)
```

### Observer Pattern

```python
from typing import Protocol, Callable

type ListenerFn = Callable[[str, object], None]

class EventEmitter:
    def __init__(self) -> None:
        self._listeners: dict[str, list[ListenerFn]] = {}

    def on(self, evento: str, fn: ListenerFn) -> None:
        self._listeners.setdefault(evento, []).append(fn)

    def emit(self, evento: str, dados: object = None) -> None:
        for fn in self._listeners.get(evento, []):
            fn(evento, dados)

class Pedido(EventEmitter):
    def __init__(self, id: int) -> None:
        super().__init__()
        self.id = id
        self._status = "pendente"

    def confirmar(self) -> None:
        self._status = "confirmado"
        self.emit("confirmado", {"pedido_id": self.id})

# Uso
pedido = Pedido(42)
pedido.on("confirmado", lambda evt, d: print(f"Email enviado para pedido {d}"))
pedido.on("confirmado", lambda evt, d: print(f"Estoque atualizado para {d}"))
pedido.confirmar()
```

### Factory Method

```python
from abc import ABC, abstractmethod
from typing import Literal

class Conexao(ABC):
    @abstractmethod
    def conectar(self) -> None: ...
    @abstractmethod
    def executar(self, query: str) -> list[dict]: ...

class ConexaoPostgres(Conexao):
    def conectar(self) -> None: print("Conectando ao PostgreSQL")
    def executar(self, query: str) -> list[dict]: return []

class ConexaoSQLite(Conexao):
    def conectar(self) -> None: print("Conectando ao SQLite")
    def executar(self, query: str) -> list[dict]: return []

def criar_conexao(tipo: Literal["postgres", "sqlite"]) -> Conexao:
    tipos: dict[str, type[Conexao]] = {
        "postgres": ConexaoPostgres,
        "sqlite": ConexaoSQLite,
    }
    if tipo not in tipos:
        raise ValueError(f"Tipo desconhecido: {tipo}")
    return tipos[tipo]()
```

### Repository Pattern com Dependency Injection

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

@dataclass
class Usuario:
    id: int
    nome: str
    email: str

class UsuarioRepository(ABC):
    @abstractmethod
    def salvar(self, usuario: Usuario) -> Usuario: ...
    @abstractmethod
    def buscar(self, id: int) -> Usuario | None: ...
    @abstractmethod
    def listar(self) -> list[Usuario]: ...

class UsuarioRepositoryMemoria(UsuarioRepository):
    def __init__(self) -> None:
        self._store: dict[int, Usuario] = {}

    def salvar(self, usuario: Usuario) -> Usuario:
        self._store[usuario.id] = usuario
        return usuario

    def buscar(self, id: int) -> Usuario | None:
        return self._store.get(id)

    def listar(self) -> list[Usuario]:
        return list(self._store.values())

class UsuarioService:
    def __init__(self, repo: UsuarioRepository) -> None:  # DIP: depende da abstração
        self._repo = repo

    def registrar(self, nome: str, email: str) -> Usuario:
        usuario = Usuario(id=len(self._repo.listar()) + 1, nome=nome, email=email)
        return self._repo.salvar(usuario)
```
