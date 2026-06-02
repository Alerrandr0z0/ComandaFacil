# 04 — Abstrações: ABC, Protocol e Duck Typing

## O Espectro de Abstração em Python

```
Duck Typing          Protocol (structural)     ABC (nominal)
     |                      |                       |
Sem contrato          Contrato implícito        Contrato explícito
Sem verificação     Verificação estática      Herança obrigatória
runtime             (mypy/pyright)            + runtime enforcement
Máx flexibilidade   Flexibilidade moderna     Máx controle
```

**Regra geral (Python moderno):**
- Novo código → `Protocol` por padrão
- Hierarquia controlada por você → `ABC`
- Duck typing puro → apenas em código simples/scripts

---

## `ABC` — Abstract Base Class

```python
from abc import ABC, abstractmethod
from typing import Any

class Repositorio(ABC):
    """Interface para qualquer repositório de dados."""

    @abstractmethod
    def salvar(self, entidade: Any) -> None:
        """Persiste a entidade."""
        ...

    @abstractmethod
    def buscar_por_id(self, id: int) -> Any | None:
        """Retorna a entidade ou None se não encontrada."""
        ...

    @abstractmethod
    def deletar(self, id: int) -> bool:
        """Retorna True se deletado, False se não encontrado."""
        ...

    # Método concreto na ABC — fornece comportamento padrão
    def existe(self, id: int) -> bool:
        return self.buscar_por_id(id) is not None

# Subclasse DEVE implementar os métodos abstratos
class RepositorioMemoria(Repositorio):
    def __init__(self) -> None:
        self._dados: dict[int, Any] = {}

    def salvar(self, entidade: Any) -> None:
        self._dados[entidade.id] = entidade

    def buscar_por_id(self, id: int) -> Any | None:
        return self._dados.get(id)

    def deletar(self, id: int) -> bool:
        return bool(self._dados.pop(id, None))

# Tentativa de instanciar ABC diretamente lança TypeError
# repo = Repositorio()  # TypeError: Can't instantiate abstract class
```

### Abstract Properties

```python
from abc import ABC, abstractmethod

class Configuracao(ABC):
    @property
    @abstractmethod
    def nome(self) -> str: ...

    @property
    @abstractmethod
    def valor(self) -> str: ...

    @abstractmethod
    def validar(self) -> bool: ...
```

---

## `Protocol` — Tipagem Estrutural Moderna

```python
from typing import Protocol, runtime_checkable

# @runtime_checkable permite usar isinstance() com o Protocol
@runtime_checkable
class Persistivel(Protocol):
    id: int

    def to_dict(self) -> dict[str, object]: ...
    def validar(self) -> bool: ...

# Qualquer classe com esses atributos/métodos satisfaz o protocolo
# SEM precisar herdar de Persistivel
class Usuario:
    def __init__(self, id: int, nome: str) -> None:
        self.id = id
        self.nome = nome

    def to_dict(self) -> dict[str, object]:
        return {"id": self.id, "nome": self.nome}

    def validar(self) -> bool:
        return bool(self.nome and self.id > 0)

# Funciona com type checkers (mypy, pyright)
def salvar_entidade(entidade: Persistivel) -> None:
    if entidade.validar():
        data = entidade.to_dict()
        print(f"Salvando: {data}")

u = Usuario(1, "Ana")
salvar_entidade(u)  # ✅ mypy aceita sem herança explícita
```

### Protocols com Métodos Padrão (Python 3.12+)

```python
from typing import Protocol

class Formato(Protocol):
    def serializar(self) -> str: ...

    def serializar_json(self) -> str:
        """Método com implementação padrão no Protocol."""
        import json
        return json.dumps({"data": self.serializar()})
```

---

## ABC vs Protocol — Guia de Escolha

```python
# Use ABC quando:
# 1. Você controla toda a hierarquia de classes
# 2. Precisa forçar implementação E fornecer comportamento padrão
# 3. Quer herança nominal (isinstance verifica herança real)
# 4. Framework/biblioteca que outros vão herdar

# Use Protocol quando:
# 1. Código de aplicação / domínio novo
# 2. Quer aceitar classes de terceiros sem modificá-las
# 3. Prefere acoplamento fraco (duck typing com type safety)
# 4. Modelando interfaces pequenas e focadas
```

### Exemplo Comparativo

```python
# Abordagem ABC
from abc import ABC, abstractmethod

class SerializadorABC(ABC):
    @abstractmethod
    def serializar(self, obj: object) -> str: ...

class JsonSerializadorABC(SerializadorABC):  # OBRIGADO a herdar
    def serializar(self, obj: object) -> str:
        import json
        return json.dumps(obj)

# Abordagem Protocol
from typing import Protocol

class Serializador(Protocol):
    def serializar(self, obj: object) -> str: ...

class JsonSerializador:  # NÃO precisa herdar
    def serializar(self, obj: object) -> str:
        import json
        return json.dumps(obj)

def processar(s: Serializador, dados: object) -> str:
    return s.serializar(dados)  # Aceita qualquer implementação
```

---

## Collections ABCs — Herde para Customização de Containers

```python
from collections.abc import MutableMapping
from typing import Iterator, Any

class CacheDict(MutableMapping[str, Any]):
    """Dict com limite de entradas (LRU simples)."""

    def __init__(self, limite: int = 100) -> None:
        self._dados: dict[str, Any] = {}
        self._limite = limite

    # MutableMapping exige __getitem__, __setitem__, __delitem__, __iter__, __len__
    def __getitem__(self, key: str) -> Any:
        return self._dados[key]

    def __setitem__(self, key: str, value: Any) -> None:
        if len(self._dados) >= self._limite and key not in self._dados:
            oldest = next(iter(self._dados))
            del self._dados[oldest]
        self._dados[key] = value

    def __delitem__(self, key: str) -> None:
        del self._dados[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._dados)

    def __len__(self) -> int:
        return len(self._dados)

    # MutableMapping fornece automaticamente: get, pop, update, keys, values, items, etc.

cache = CacheDict(limite=3)
cache["a"] = 1
cache.update({"b": 2, "c": 3})  # usa MutableMapping.update()
print("a" in cache)  # usa MutableMapping.__contains__()
```

---

## `__init_subclass__` — Hook Moderno (Alternativa a Metaclasse)

```python
class PluginBase:
    _registrado: dict[str, type] = {}

    def __init_subclass__(cls, tipo: str | None = None, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if tipo:
            PluginBase._registrado[tipo] = cls

class PluginPDF(PluginBase, tipo="pdf"):
    def processar(self) -> str:
        return "Processando PDF"

class PluginCSV(PluginBase, tipo="csv"):
    def processar(self) -> str:
        return "Processando CSV"

# Auto-registro sem metaclasse
print(PluginBase._registrado)
# {'pdf': <class 'PluginPDF'>, 'csv': <class 'PluginCSV'>}
```
