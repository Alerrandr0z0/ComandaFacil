# ComandaFácil 🍽️

Sistema de gerenciamento de comandas para restaurantes com arquitetura CQRS, DDD e multi-tenancy.

## Stack

| Camada | Tecnologia |
|--------|-----------|
| **Backend** | Python 3.12 + FastAPI + SQLAlchemy (Postgres) + Motor (MongoDB) |
| **Frontend** | React 19 + Vite 8 + TypeScript 6 + Tailwind CSS 4 |
| **Qualidade** | Ruff + Pyright + Pytest + Vitest + Mutmut + Stryker |
| **Infra** | Docker Compose (Postgres + MongoDB) |

## Arquitetura

```
Monorepo:
├── backend/       → API REST (CQRS)
│   └── app/{contexto}/
│       ├── domain/        → Lógica pura (sem I/O)
│       ├── application/   → Commands/Queries (orquestração)
│       ├── infrastructure/→ Repositórios (SQLAlchemy/Motor)
│       └── api/           → Rotas FastAPI (finas)
└── frontend/      → SPA React
    └── src/features/{contexto}/
        └── components/    → Componentes por contexto
```

**CQRS:** Postgres como write database, MongoDB como read model.
**Multi-tenancy:** `X-Tenant-ID` header → `ContextVar`.
**Arquitetura Baseada em Eventos (EDA):** Totalmente desacoplada na camada de banco de dados e APIs via `EventBus` e Outbox Pattern.
- Quando um item é adicionado ou a comanda é cancelada no contexto **Order**, eventos de domínio (`OrderItemAdded`, `OrderCancelled`) são publicados de forma transacional.
- O contexto **Kitchen (KDS)** consome esses eventos para criar ou cancelar os cartões de preparo de forma assíncrona.
- Ao mudar o status de um item na cozinha (ex: finalizado), o evento `KitchenItemStatusChanged` é gerado, fazendo com que o contexto **Stock** debite os insumos da receita automaticamente e o contexto **Order** atualize o status da comanda.

### Contextos (Bounded Contexts)

`auth` · `menu` · `order` · `kitchen` · `payment` · `stock` · `analytics`

## Quick Start

```bash
make setup           # uv sync + npm install + pre-commit
make start           # docker compose up -d (Postgres + MongoDB)
make migrate         # Aplica as migrations do banco de dados (Alembic)
make dev             # backend :8000 + frontend :5180
```

### Mock Seeder (Barraca do Sol)

Para rodar a aplicação com a base simulada de um restaurante de praia (cardápio com 16 itens, estoque integrado, comandas ativas na KDS, pagamentos e histórico para o Analytics):

```bash
cd backend && uv run python scratch/seed_beach_restaurant.py
```

## Qualidade

| Gate | Backend | Frontend |
|------|---------|----------|
| Lint | Ruff (100 cols) | Biome (single quotes) |
| Types | Pyright (strict) | tsc --noEmit |
| Tests | Pytest (80% cov) | Vitest (80% cov) |
| Mutação | Mutmut | Stryker |
| Propriedade | Hypothesis | fast-check |
| Complexidade | complexipy (≤15) | - |
| Segurança | Bandit | - |
| E2E | - | Playwright |
