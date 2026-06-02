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

### Contextos (Bounded Contexts)

`auth` · `menu` · `order` · `kitchen` · `payment` · `stock` · `analytics`

## Quick Start

```bash
make setup           # uv sync + npm install + pre-commit
make start           # docker compose up -d (Postgres + MongoDB)
make dev             # backend :8000 + frontend :5173
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
