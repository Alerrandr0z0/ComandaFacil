# ComandaFácil — Backend

API REST com CQRS, DDD e multi-tenancy.

## Stack

- **Runtime:** Python 3.12 + FastAPI
- **Write DB:** PostgreSQL + SQLAlchemy (async)
- **Read DB:** MongoDB + Motor (async)
- **Validação:** Pydantic v2 (apenas DTOs/API)
- **Domain Objects:** `@dataclass(frozen=True)` (Value Objects imutáveis)

## Estrutura

```
app/{contexto}/
├── domain/          → Entidades puras, sem imports de I/O
├── application/     → Commands e Queries (casos de uso)
├── infrastructure/  → Repositórios (SQLAlchemy, Motor), ORM, sync
└── api/             → Rotas FastAPI (delegam para application)

tests/
├── unit/            → Síncronos, sem async
├── integration/     → Testcontainers (Postgres + MongoDB reais)
└── property/        → Hypothesis
```

## Comandos

| Comando | Descrição |
|---------|-----------|
| `uv run fastapi dev app/main.py` | Dev server (hot-reload) |
| `uv run ruff check .` | Lint |
| `uv run ruff format .` | Format |
| `uv run pyright` | Typecheck |
| `uv run pytest tests/ --cov=app --cov-fail-under=80 -v` | Testes |
| `uv run complexipy app/ --max-complexity-allowed 15` | Complexidade |
| `uv run bandit -r app/ -s B101 -ll` | Segurança |
| `uv run alembic upgrade head` | Migrations |

## Logging

Logs em JSON para stdout via `TenantAwareJsonFormatter`. Tenant ID injetado automaticamente.
