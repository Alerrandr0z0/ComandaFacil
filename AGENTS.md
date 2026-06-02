# ComandaFácil — Agent Guide

## Quick Start

```bash
make setup           # uv sync + npm install + pre-commit hooks
make start           # docker compose up -d (Postgres 5432, MongoDB 27017)
make dev             # backend :8000 + frontend :5173 in parallel
```

## Toolchain

### Backend (`backend/`)
| Command | What |
|---------|------|
| `uv run fastapi dev app/main.py` | Dev server (hot-reload) |
| `uv run ruff check .` | Lint (100 cols, ~40 rulesets) |
| `uv run ruff format .` | Format |
| `uv run pyright` | Typecheck (strict mode) |
| `uv run complexipy app/ --max-complexity-allowed 15` | Cognitive complexity gate |
| `uv run pytest tests/ --cov=app --cov-fail-under=80 -v` | Full test suite |
| `uv run pytest tests/unit/ -m hypothesis -v` | Property-based tests only |
| `uv run bandit -r app/ -s B101 -ll` | Security scan |
| `uv run alembic upgrade head` | Apply migrations |
| `make mutation-incr PATHS='app/auth/...' TESTS='tests/unit/auth/'` | Incremental mutation |

### Frontend (`frontend/`)
| Command | What |
|---------|------|
| `npm run dev` | Vite HMR dev server |
| `npm run lint` | Biome check |
| `npm run fix` | Biome autofix |
| `npm run typecheck` | `tsc --noEmit` |
| `npm run test` | Vitest (jsdom, 80% coverage threshold) |
| `npm run test:property` | fast-check property tests |
| `npm run e2e` | Playwright |
| `make types-gen` | Generate TS types from FastAPI OpenAPI schema |

## Architecture

**Monorepo:** `backend/` (Python 3.12 + FastAPI + uv) + `frontend/` (React 19 + Vite 8 + TS 6.0 strict)

**DDD per bounded context** under `app/{context}/`:
```
domain/    → pure logic, zero I/O imports, frozen Value Objects
application/ → commands/queries, orchestrates domain → repo → events
infrastructure/ → implements domain interfaces (SQLAlchemy repos)
api/       → thin FastAPI routes, delegates to application
```

**Contexts:** `auth`, `menu`, `order`, `kitchen`, `payment`, `stock`, `analytics`

**Key rules:**
- Domain never imports `sqlalchemy`, `motor`, `fastapi`, `httpx`
- No cross-context imports (use shared Value Object IDs or Domain Events)
- All state changes go through Aggregate Root
- Multi-tenant via `X-Tenant-ID` header → `ContextVar`

**Databases:** Postgres (write) + MongoDB (read models). Stateful sessions (DB-stored, not stateless JWT).

## Testing

- **Naming:** `test_{action}_when_{condition}_then_{expected_result}`
- **Structure:** AAA (Arrange/Act/Assert) with section comments
- **Unit tests** are synchronous (domain must be pure — no async in domain tests)
- **Integration tests** use testcontainers (real Postgres/MongoDB)
- **Markers:** `hypothesis` (property-based), `slow` (exclude with `-m 'not slow'`)
- **Conftest layered:** `tests/integration/conftest.py` has `settings` and `client` (FastAPI app). `tests/unit/conftest.py` has only `settings` (no `app.main` dependency).
- Mutmut v3 uses `tests_dir` and `paths_to_mutate` in `pyproject.toml` (no CLI flags). `also_copy` lists files outside mutation scope needed by tests.
- Never mock what you don't own; domain entities are never mocked

## Frontend (`frontend/`)

**Sobre `openapi-typescript`**: peer dep `typescript@^5.x` conflita com nosso `^6.0.0`. Resolvido via `overrides` em `package.json` — mantém TS 6 sem bloqueios no `npm ci`.

### Rotas
| Path | Página | Auth |
|------|--------|:----:|
| `/login` | Login | ❌ |
| `/orders` | Comandas (TableGrid + OrderDraft + CheckoutFlow) | ✅ |
| `/kitchen` | KDS (Kanban WebSocket) | ✅ |
| `/stock` | Estoque (StockManager) | ✅ |
| `/analytics` | Dashboard (Recharts) | ✅ |

### Padrões
- React Query para server state + Context para auth/tenant
- Axios com interceptors (injecta `X-Tenant-ID` + `Authorization`)
- WebSocket raw na KDS
- Tailwind v4 dark custom (gray-950 + brand-500 + glassmorphism)

## Conventions

- **Backend:** Ruff (double quotes, spaces), Pyright strict, `__repr__` on all classes
- **Frontend:** Biome (single quotes, as-needed semicolons, space indent 2, width 100)
- **TS paths:** `@/` maps to `src/`
- Avoid Pydantic for internal domain objects — use `@dataclass(frozen=True)` for Value Objects
- `ClassVar` for class attributes, `Final` for constants

## Skills (`.opencode/skills/`)
- `comandafacil-tdd-refactor` — mandatory RED→GREEN→REFACTOR→MUTATE cycle
- `comandafacil-ddd-guard` — layer boundary enforcement
- `comandafacil-git-workflow` — Conventional Commits, branch naming, PR checklist
- `oop-python` — OOP Python reference

## CI Pipeline (`.github/workflows/ci.yml`)
Runs on push/PR to `main`. Backend: ruff lint + format check → pyright → complexipy → bandit → pytest. Frontend: biome lint → tsc → vitest.

## Problemas Conhecidos no CI

| Problema | Causa | Status |
|----------|-------|--------|
| `openapi-typescript` falha no `npm ci` | peer dep `typescript@^5.x` vs nosso `^6.0.0` | Fix: `overrides` em `package.json` |
| `ruff format --check` falha | Formatação não aplicada localmente | Rodar `ruff format .` antes do push |

## Relatório Técnico
- `RELATORIO_TECNICO.docx` — gerado via Pandoc + Mermaid CLI (mmdc + Puppeteer Chromium)
- `RELATORIO_TECNICO_IMAGENS.md` — markdown fonte com PNG embutidos
- `diagramas/` — arquivos .mmd, .svg, .png dos diagramas
- Comando para regenerar: `pandoc RELATORIO_TECNICO_IMAGENS.md -o RELATORIO_TECNICO.docx --from=gfm --to=docx --resource-path=.`

## Logging

`backend/app/shared/logging.py` — `TenantAwareJsonFormatter` + `setup_logging()`. Logs em JSON p/ stdout (não mais arquivos por tenant). ADR 002 atualizado (cloud-native).
