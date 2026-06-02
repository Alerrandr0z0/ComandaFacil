---
name: comandafacil-ddd-guard
description: >-
  DDD Architecture Guard for the ComandaFácil monorepo. Enforces strict layer
  separation (Domain/Application/Infrastructure/API), prevents cross-context
  imports, mandates Value Object immutability, Aggregate Root patterns, and
  Domain Event emission on state changes.
---

# ComandaFácil — DDD Architecture Guard

## Overview

This skill acts as an architectural watchdog. Before writing or modifying any
file in a Bounded Context, the agent MUST consult this skill to verify that
the change respects the DDD layer boundaries, import rules, and design
patterns defined for the ComandaFácil system.

**When to activate**: Every time the agent creates, modifies, or moves a file
inside `app/{bounded_context}/`.

---

## Bounded Contexts

The following Bounded Contexts are defined. Each is a self-contained module
under `app/`:

| Context | Responsibility | Key Aggregates |
|---------|---------------|----------------|
| `auth` | Autenticação, autorização, multi-tenancy | User, Role, Token |
| `menu` | Cardápio, categorias, itens, preços | MenuItem, Category |
| `order` | Pedidos, itens do pedido, status | Order, OrderItem |
| `kitchen` | Fila de preparo, tempos, prioridade | KitchenTicket |
| `payment` | Pagamentos, Stripe, notas fiscais | Payment, Invoice |
| `stock` | Estoque, movimentações, alertas | StockItem, StockMovement |
| `analytics` | Dashboards, relatórios, métricas | (Read Models only) |

---

## Layer Architecture (per Bounded Context)

```
app/{context}/
├── domain/              ← Regras de negócio puras (ZERO I/O)
│   ├── entities.py      ← Aggregate Roots e Entidades
│   ├── value_objects.py ← Value Objects (imutáveis)
│   ├── events.py        ← Domain Events
│   ├── services.py      ← Domain Services (lógica que não pertence a uma entidade)
│   └── exceptions.py    ← Exceções de domínio específicas do contexto
├── application/         ← Orquestração (Commands, Queries, Use Cases)
│   ├── commands.py      ← Command handlers (escrita → Postgres)
│   ├── queries.py       ← Query handlers (leitura → MongoDB)
│   └── services.py      ← Application Services
├── infrastructure/      ← Implementações concretas (Repos, ORMs, Sync)
│   ├── orm_models.py    ← SQLAlchemy ORM models
│   ├── repositories.py  ← Implementações dos repositórios
│   └── mongo_sync.py    ← Sincronização Postgres → MongoDB
└── api/
    └── routes.py        ← Endpoints FastAPI (thin controller)
```

---

## Import Rules — Dependency Flow

A dependência entre camadas é **unidirecional e de cima para baixo**:

```
  API  →  Application  →  Domain
   ↓          ↓
Infrastructure
```

### Import Validation Matrix

| Arquivo em... | Pode importar de... | NÃO pode importar de... |
|--------------|---------------------|------------------------|
| `domain/*` | `domain/*` (mesmo contexto), `app/shared/value_objects.py`, `app/shared/exceptions.py` | ❌ `application/`, ❌ `infrastructure/`, ❌ `api/`, ❌ `sqlalchemy`, ❌ `motor`, ❌ `fastapi`, ❌ outro `app/{context}/` |
| `application/*` | `domain/*` (mesmo contexto), `app/shared/*` | ❌ `infrastructure/` (usa interfaces/ports), ❌ `api/`, ❌ `sqlalchemy`, ❌ `motor`, ❌ outro `app/{context}/` |
| `infrastructure/*` | `domain/*`, `application/*` (mesmo contexto), `app/shared/*`, `sqlalchemy`, `motor` | ❌ `api/`, ❌ outro `app/{context}/` |
| `api/routes.py` | `application/*` (mesmo contexto), `app/dependencies.py`, `app/shared/*`, `fastapi` | ❌ `domain/` diretamente (passa pela Application), ❌ `infrastructure/` diretamente, ❌ outro `app/{context}/` |

### The Cardinal Rule: No Cross-Context Imports

```python
# ❌ PROIBIDO — Nunca importar de outro Bounded Context
from app.order.domain.entities import Order  # dentro de app/payment/

# ✅ CORRETO — Comunicação entre contextos usa Domain Events ou shared IDs
from app.shared.value_objects import OrderId  # ID compartilhado como Value Object
```

Se dois contextos precisam colaborar, a comunicação acontece via:
1. **Domain Events** (publicação e assinatura assíncrona)
2. **Shared Value Objects** em `app/shared/value_objects.py` (apenas IDs e tipos primitivos)

---

## Design Pattern Rules

### 1. Value Objects — Imutabilidade Obrigatória

Todo Value Object DEVE ser imutável usando `frozen=True` no Pydantic:

```python
from pydantic import BaseModel

class Money(BaseModel, frozen=True):
    """Value Object imutável para valores monetários."""
    amount: Decimal
    currency: str = "BRL"
```

**Teste**: Se um Value Object permite `obj.amount = 10`, a arquitetura está errada.

### 2. Aggregate Root — Ponto Único de Modificação

Todas as modificações de estado DEVEM passar pelo Aggregate Root:

```python
# ✅ CORRETO — Mudança via Aggregate Root
order.add_item(item)
order.confirm()

# ❌ PROIBIDO — Modificação direta de entidade filha
order.items[0].quantity = 5  # Viola encapsulamento
```

### 3. Domain Events — Emissão Obrigatória em Mudanças de Estado

Quando um Aggregate Root muda de estado, ele DEVE emitir um Domain Event:

```python
class Order:
    def confirm(self) -> None:
        self.status = OrderStatus.CONFIRMED
        self._events.append(OrderConfirmedEvent(
            order_id=self.id,
            tenant_id=self.tenant_id,
            confirmed_at=datetime.now(tz=UTC),
        ))
```

### 4. Repository Pattern — Interface no Domain, Implementação na Infrastructure

```python
# domain/repositories.py (PORT — interface abstrata)
from abc import ABC, abstractmethod

class OrderRepository(ABC):
    @abstractmethod
    async def save(self, order: Order) -> None: ...

    @abstractmethod
    async def find_by_id(self, order_id: OrderId) -> Order | None: ...

# infrastructure/repositories.py (ADAPTER — implementação concreta)
class SqlAlchemyOrderRepository(OrderRepository):
    def __init__(self, session: AsyncSession) -> None: ...
```

### 5. Application Services — Orquestração Fina

Application Services orquestram Domain → Repository → Events.
Eles NÃO contêm regras de negócio:

```python
class CreateOrderCommand:
    async def execute(self, dto: CreateOrderDTO) -> OrderId:
        # 1. Criar aggregate via domain
        order = Order.create(tenant_id=dto.tenant_id, items=dto.items)
        # 2. Persistir via repository (port)
        await self.repo.save(order)
        # 3. Publicar events
        for event in order.collect_events():
            await self.event_bus.publish(event)
        return order.id
```

---

## Pre-Flight Checklist

Before committing ANY change inside a Bounded Context, verify:

- [ ] **Import check**: No imports violating the matrix above
- [ ] **No cross-context imports**: No `from app.{other_context}` inside the current context
- [ ] **Domain purity**: `domain/` has ZERO imports from `sqlalchemy`, `motor`, `fastapi`, `httpx`
- [ ] **Value Objects frozen**: All VOs use `frozen=True`
- [ ] **State changes via Aggregate Root**: No direct child entity mutation
- [ ] **Domain Events emitted**: State transitions produce events
- [ ] **Repository as port**: Domain defines abstract interface, infra implements it
- [ ] **API is thin**: Routes delegate to Application Services, no business logic in routes

---

## Anti-Patterns to Detect

| Anti-Pattern | What It Looks Like | Correction |
|-------------|-------------------|------------|
| **Anemic Domain Model** | Entities are just data bags with no methods; all logic in services | Move behavior into entities and aggregate roots |
| **Smart Controller** | Business logic in `api/routes.py` | Extract to Application Service → Domain |
| **God Service** | One service handling everything in a context | Split by use case / command |
| **Leaky Abstraction** | Domain entity importing `Column` from SQLAlchemy | Separate ORM model from domain entity |
| **Context Coupling** | `app/order/` importing from `app/menu/` | Use shared Value Object IDs or Domain Events |
| **Mutable Value Object** | Value Object without `frozen=True` | Add `frozen=True` to class definition |
