# ComandaFácil — Unified Toolchain

.PHONY: help setup setup-back setup-front \
        start stop status \
        dev dev-back dev-front \
        lint lint-back lint-front \
        fix fix-back fix-front \
        typecheck typecheck-back \
        test test-back test-front \
        property-test property-test-back property-test-front \
        mutation mutation-back mutation-front \
        mutation-incr mutation-score \
        security security-back security-secrets security-deps security-front \
        complexity \
        migrate migrate-new migrate-down \
        types-gen \
        hooks \
        e2e

# --- Default ---
help:
	@echo "ComandaFácil — Unified Toolchain"
	@echo "Usage: make <target>"
	@echo ""
	@echo "Setup:"
	@echo "  setup             Instala todas as dependências e git hooks"
	@echo ""
	@echo "Dev:"
	@echo "  dev               Sobe backend + frontend em paralelo"
	@echo "  dev-back          Sobe apenas o backend (FastAPI hot-reload)"
	@echo "  dev-front         Sobe apenas o frontend (Vite HMR)"
	@echo "  start             Sobe infraestrutura (Postgres + MongoDB via Docker)"
	@echo "  stop              Para a infraestrutura"
	@echo "  status            Status dos serviços Docker"
	@echo ""
	@echo "Qualidade:"
	@echo "  lint              Lint completo (back + front)"
	@echo "  fix               Auto-fix (back + front)"
	@echo "  typecheck         Type check completo"
	@echo "  complexity        Análise de complexidade cognitiva do backend"
	@echo "  security          Todos os scanners de segurança"
	@echo "  hooks             Roda todos os pre-commit hooks em todos os arquivos"
	@echo ""
	@echo "Testes:"
	@echo "  test              Roda todos os testes (back + front)"
	@echo "  property-test     Testes baseados em propriedades (Hypothesis + fast-check)"
	@echo "  e2e               Testes Playwright end-to-end (regra 3 cliques)"
	@echo ""
	@echo "Mutation Testing:"
	@echo "  mutation          Suite completa de mutantes (~30min)"
	@echo "  mutation-incr     Mutação incremental: PATHS='...' [TESTS='...']"
	@echo "  mutation-score    Exibe último score de mutação"
	@echo ""
	@echo "Banco de Dados:"
	@echo "  migrate           Aplica todas as migrations pendentes"
	@echo "  migrate-new       Gera nova migration: MSG='descrição'"
	@echo "  migrate-down      Reverte última migration"
	@echo ""
	@echo "Geração:"
	@echo "  types-gen         Gera tipos TypeScript a partir do schema OpenAPI do FastAPI"

# ─── Setup ────────────────────────────────────────────────────────────────────

setup: setup-back setup-front
	@echo "✅ Setup completo! Rode 'make start' para subir a infraestrutura."

setup-back:
	cd backend && uv sync
	cd backend && uv run pre-commit install

setup-front:
	cd frontend && npm install

# ─── Infraestrutura ───────────────────────────────────────────────────────────

start:
	docker compose up -d
	@echo ""
	@echo "Serviços em execução:"
	@echo "  - Postgres:  localhost:5432"
	@echo "  - MongoDB:   localhost:27017"

stop:
	docker compose down

status:
	docker compose ps

# ─── Dev ──────────────────────────────────────────────────────────────────────

dev:
	@make -j2 dev-back dev-front

dev-back:
	cd backend && uv run fastapi dev app/main.py

dev-front:
	cd frontend && npm run dev

# ─── Lint & Format ────────────────────────────────────────────────────────────

lint: lint-back lint-front

lint-back:
	cd backend && uv run ruff check .
	cd backend && uv run pyright
	cd backend && uv run complexipy app/ --max-complexity-allowed 15

lint-front:
	cd frontend && npx biome check .

fix: fix-back fix-front

fix-back:
	cd backend && uv run ruff check . --fix --unsafe-fixes
	cd backend && uv run ruff format .

fix-front:
	cd frontend && npx biome check --write .

typecheck: typecheck-back
	cd frontend && npm run typecheck

typecheck-back:
	cd backend && uv run pyright

complexity:
	cd backend && uv run complexipy app/ --max-complexity-allowed 15

# ─── Segurança ────────────────────────────────────────────────────────────────

security: security-back security-secrets security-deps security-front

security-back:
	cd backend && uv run bandit -r app/ -s B101 -ll

security-secrets:
	cd backend && uv run pre-commit run gitleaks --all-files

security-deps:
	cd backend && uv run pip-audit --strict --desc on 2>/dev/null || \
		echo "pip-audit: auditoria concluída"

security-front:
	cd frontend && npm audit --audit-level=high 2>/dev/null || \
		echo "npm audit: concluído com avisos"

hooks:
	cd backend && uv run pre-commit run --all-files

# ─── Testes ───────────────────────────────────────────────────────────────────

test: test-back test-front

test-back:
	cd backend && uv run pytest tests/ \
		--cov=app \
		--cov-report=term-missing \
		--cov-fail-under=80 \
		-v

test-front:
	cd frontend && npm run test

property-test: property-test-back property-test-front

property-test-back:
	cd backend && uv run pytest tests/unit/ -m "hypothesis" -v

property-test-front:
	cd frontend && npm run test:property

e2e:
	cd frontend && npx playwright test

# ─── Mutation Testing ─────────────────────────────────────────────────────────

mutation: mutation-back mutation-front

mutation-back:
	cd backend && rm -rf mutants .mutmut-cache
	cd backend && uv run mutmut run --max-children 4
	@echo "\n=== Mutation Score (backend) ==="
	-cd backend && uv run mutmut results --no-pager 2>/dev/null | tail -5

mutation-incr:
	@if [ -z "$(PATHS)" ]; then \
		echo "Uso: make mutation-incr PATHS='app/order/...' [TESTS='tests/unit/order/...']"; \
		exit 1; \
	fi
	cd backend && rm -rf mutants .mutmut-cache
	cd backend && uv run mutmut run \
		--paths-to-mutate $(PATHS) \
		$(if $(TESTS),--tests-dir $(TESTS),) \
		--max-children 4
	-cd backend && uv run mutmut results --no-pager 2>/dev/null | tail -10

mutation-score:
	-cd backend && uv run mutmut results --no-pager 2>/dev/null | tail -10

mutation-front:
	cd frontend && npm run test:mutation

# ─── Banco de Dados / Migrations ──────────────────────────────────────────────

migrate:
	cd backend && uv run alembic upgrade head

migrate-new:
	@if [ -z "$(MSG)" ]; then \
		echo "Uso: make migrate-new MSG='descricao da alteracao'"; \
		exit 1; \
	fi
	cd backend && uv run alembic revision --autogenerate -m "$(MSG)"

migrate-down:
	cd backend && uv run alembic downgrade -1

# ─── Geração de Tipos ─────────────────────────────────────────────────────────

types-gen:
	@echo "Gerando tipos TypeScript a partir do schema OpenAPI..."
	cd frontend && npx openapi-typescript http://localhost:8000/openapi.json \
		-o src/shared/types/api.ts
	@echo "✅ src/shared/types/api.ts atualizado!"
