---
name: comandafacil-tdd-refactor
description: >-
  Ultra-rigorous Test-Driven Development and Refactoring workflow for the
  ComandaFácil monorepo. Enforces Red-Green-Refactor-Mutate with property-based
  testing, strict static analysis (Ruff/Pyright/Biome), mutation testing
  (Mutmut/Stryker), anti-rationalization gates, and Conventional Commits.
---

# ComandaFácil — Ultra-Rigorous TDD & Refactoring Skill

## Overview

Zero-tolerance TDD workflow for the ComandaFácil monorepo. Every line of
production code MUST be driven by a failing test. Code written without a
prior failing test MUST be deleted and restarted from RED.

## Dependencies

| Layer | Backend (Python) | Frontend (TS/React) |
|-------|-----------------|---------------------|
| Unit Tests | `pytest`, `pytest-asyncio` | `vitest` |
| Property Tests | `hypothesis` | `fast-check` |
| Mutation Tests | `mutmut` | `stryker` |
| Type Checking | `pyright` (strict) | `biome` + `tsconfig` (strict) |
| Lint & Format | `ruff` | `biome` |
| Complexity | `complexipy` (max 15) | — |
| Security | `bandit` | `npm audit` |
| Orchestration | Root `Makefile` | Root `Makefile` |

---

## Test Pyramid — Enforced Ratios

```
        ╱╲
       ╱ E2E ╲          ~5%  — Playwright (regra 3 cliques)
      ╱────────╲
     ╱Integration╲      ~15% — Testcontainers (Postgres/MongoDB reais)
    ╱──────────────╲
   ╱   Unit Tests   ╲   ~80% — pytest / vitest (puro, sem I/O)
  ╱──────────────────╲
```

**Decision matrix — qual tipo de teste escrever:**

| Situação | Tipo | Justificativa |
|----------|------|---------------|
| Regra de domínio, cálculo, validação de Value Object | Unit | Puro, sem dependência externa |
| Transição de estado de Aggregate Root | Unit + Property-Based | `Hypothesis` explora edge cases |
| Repository salvando/lendo entidade real | Integration | Precisa de DB real via Testcontainers |
| Fluxo completo de API endpoint | Integration | `AsyncClient` + `ASGITransport` |
| Jornada do usuário (ex: login → criar pedido) | E2E | Playwright no frontend |

---

## Test Naming Convention

### Backend (Python)
```python
# Arquivo: tests/unit/{bounded_context}/test_{module}.py
# Classe:  Test{Component}{Behavior}
# Método:  test_{action}_when_{condition}_then_{expected_result}

class TestJwtTokenGeneration:
    def test_create_token_when_valid_tenant_then_returns_signed_jwt(self) -> None: ...
    def test_create_token_when_empty_tenant_id_then_raises_value_error(self) -> None: ...
```

### Frontend (TypeScript)
```typescript
// Arquivo: src/features/{feature}/__tests__/{module}.test.ts
// describe("{Component} - {Behavior}")
// it("should {expected} when {condition}")

describe("OrderPrice - Calculation", () => {
  it("should apply discount when coupon is valid", () => { ... });
});
```

---

## Test Body Structure — AAA (Arrange-Act-Assert)

Every test body MUST follow the **Arrange-Act-Assert** pattern with explicit
section comments for readability:

```python
def test_create_order_when_items_provided_then_calculates_total(self) -> None:
    # Arrange
    items = [OrderItem(name="Pizza", price=Decimal("39.90"), quantity=2)]

    # Act
    order = Order.create(tenant_id="franquia_001", items=items)

    # Assert
    assert order.total == Decimal("79.80")
    assert order.status == OrderStatus.PENDING
```

---

## When to Use Property-Based Tests (Hypothesis / fast-check)

Use Property-Based Testing when ANY of these conditions apply:

| Condition | Example |
|-----------|---------|
| Mathematical calculation or transformation | Total de pedido, desconto percentual, troco |
| State machine / transition rules | `OrderStatus`: PENDING → CONFIRMED → PREPARING → DONE |
| Serialization / deserialization roundtrip | `to_dict()` → `from_dict()` deve retornar objeto igual |
| Invariant that must hold for ALL inputs | `price > 0`, `quantity >= 1`, `tenant_id não-vazio` |
| Boundary / edge-case-heavy logic | Estoque mínimo, limites de quantidade, timezone handling |

For simple CRUD wiring or configuration, a standard `pytest` test suffices.

---

## Async Test Patterns (FastAPI / Motor)

All async tests MUST use `pytest-asyncio` with the project's `asyncio_mode = "auto"`:

```python
# Integration test with real FastAPI app
async def test_health_check_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

**Rule**: Domain unit tests MUST be synchronous. Only infrastructure/integration
tests should be async. If your domain test needs `async`, your domain layer is
leaking I/O — fix the architecture, not the test.

---

## Mocking Guidelines (DDD + CQRS Context)

| Layer | Mock Strategy |
|-------|---------------|
| **Domain** (`domain/entities.py`, `domain/value_objects.py`) | **NEVER mock**. Test with real objects. Domain is pure logic. |
| **Application** (`application/services.py`, `application/commands.py`) | Mock the **Repository interface** (port). Inject a fake/in-memory implementation. |
| **Infrastructure** (`infrastructure/repositories.py`) | **Do NOT mock** the database. Use Testcontainers with real Postgres/MongoDB. |
| **API** (`api/routes.py`) | Use `AsyncClient` with `ASGITransport`. Mock the Application Service if testing the route in isolation. |

**Anti-pattern**: Never mock what you don't own (e.g., SQLAlchemy internals,
Motor cursors). Test those through integration tests with real databases.

---

## Workflow — The 4-Phase Cycle

### Phase 1: RED (Specification)

1. **Write ONE atomic test** following AAA and the naming convention above.
2. **Run the test**: `cd backend && uv run pytest tests/unit/{context}/ -x -v`
3. **Verify CORRECT failure**:
   - ✅ `ImportError` (module/class doesn't exist yet) → proceed
   - ✅ `AssertionError` (wrong value returned) → proceed
   - ❌ `SyntaxError`, `IndentationError` → fix the TEST first, it's malformed
4. **Show the traceback to the user** and confirm before proceeding.

### Phase 2: GREEN (Minimal Implementation)

1. Write the **absolute minimum code** to make the test pass.
   - Positive constraint: "Write only the code required to satisfy the assert."
2. Run the test: confirm GREEN.
3. Run ALL tests in the bounded context: `cd backend && uv run pytest tests/unit/{context}/ -v`
   - Ensure no regressions.

### Phase 3: REFACTOR (Quality Gates)

Execute these checks **in order**. ALL must pass before proceeding.

```bash
# 1. Auto-format (fixes trivial issues automatically)
make fix-back

# 2. Lint (must be 0 errors)
cd backend && uv run ruff check .

# 3. Type check (must be 0 errors, 0 warnings)
cd backend && uv run pyright

# 4. Complexity (max cognitive complexity = 15)
cd backend && uv run complexipy app/{context}/ --max-complexity-allowed 15

# 5. All tests still green
cd backend && uv run pytest tests/ -v

# 6. Security scan (no high/critical findings)
cd backend && uv run bandit -r app/{context}/ -s B101 -ll
```

**Breaking change rule**: If refactoring requires altering a public method
signature, the agent MUST:
1. Stop immediately.
2. Explain the impact (which files/tests break).
3. Obtain explicit user authorization.

### Phase 4: MUTATE (Test Effectiveness Validation)

1. Run incremental mutation testing:
   ```bash
   make mutation-incr PATHS='app/{context}/{file}.py' TESTS='tests/unit/{context}/'
   ```
2. Inspect surviving mutants. For each survivor:
   - Understand what logical change the mutant made.
   - If the mutant is **equivalent** (no observable behavior change), document it
     and move on — equivalence is mathematically undecidable and ~40% of
     survivors in real codebases can be equivalent.
   - If **non-equivalent**, write a new test case that catches that exact change.
3. Target mutation score on modified lines:
   - **≥ 80%** for critical modules (`auth`, `payment`, `order`)
   - **≥ 70%** for standard modules (`menu`, `stock`, `analytics`)
   - **Do NOT chase 100%** — diminishing returns plateau around 80%.
4. Present summary to the user:
   - Clean diff of changes
   - Type-check report (0 errors)
   - Mutation score with threshold context

---

## Conventional Commits

Every commit produced during TDD MUST follow Conventional Commits format:

```
<type>(<scope>): <description>

[optional body]
```

| Phase | Commit Format | Example |
|-------|--------------|---------|
| RED (test written) | `test(auth): add jwt token generation test` | Test file only |
| GREEN (impl passes) | `feat(auth): implement jwt token service` | Implementation only |
| REFACTOR | `refactor(auth): extract token config to value object` | Refactored code |
| MUTATE (fix) | `test(auth): kill surviving mutant in token expiry` | Additional test |

**Types**: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`, `perf`
**Scope**: Always the bounded context name (`auth`, `menu`, `order`, etc.)

---

## Anti-Rationalization Table

When the agent tries to skip a step, consult this table. These are NOT valid
excuses:

| Excuse | Rebuttal |
|--------|----------|
| "This is a trivial change, it doesn't need a test." | All production code needs a test. "Trivial" changes cause production bugs. Write the test. |
| "I'll add tests later." | No. TDD means test FIRST. Delete the code and start from RED. |
| "The type system already catches this." | Types verify structure, not behavior. Write a behavioral test. |
| "This is just a one-line fix." | One-line fixes are the easiest to test. Write the test. |
| "Running mutation testing takes too long for this." | Use `mutation-incr` with targeted PATHS. It takes seconds for a single file. |
| "The refactor is too small to need lint/typecheck." | Run the full quality gate. Small refactors introduce subtle type regressions. |
| "I can't test this because it depends on the database." | Domain logic MUST NOT depend on the database. Fix the architecture. |
| "Property-based testing is overkill here." | If it involves math, state transitions, or invariants, it's NOT overkill. Check the decision table. |
| "This is just infrastructure/glue code." | Infrastructure gets integration tests with Testcontainers. No code goes untested. |

---

## Golden Rules for AI-Driven TDD

1. **One-at-a-Time (Granularity)**: One failing test → one minimal implementation → one refactor cycle. Never batch multiple features.

2. **Behavioral Testing (Loose Coupling)**: Test inputs/outputs at component boundaries. Never test private methods or internal state directly.

3. **Atomic Git Commits**: Commit after every GREEN and every REFACTOR. Enables cheap reverts.

4. **Positive Constraints**: Instead of "don't over-engineer," say "write only the code required to satisfy the assert."

5. **Vertical Slices**: Implement features as complete vertical slices through the architecture (test + domain + application + route) rather than building horizontal layers across the whole system.

6. **Domain Tests are Synchronous**: If a domain unit test requires `async`, the domain layer is leaking I/O. Fix the design.

7. **Format Before Lint**: Always run `make fix-back` before `make lint`. Don't waste cycles on fixable formatting issues.

---

## Common Mistakes

1. **Over-Engineering in GREEN**: Writing abstractions or patterns not yet demanded by a test.
2. **Wrong Failure in RED**: Proceeding when the test failed due to a syntax error instead of a logical absence.
3. **Ignoring Surviving Mutants**: Surviving mutants = weak tests. Always kill them.
4. **Silent Breaking Changes**: Changing public interfaces without user approval.
5. **Tightly-Coupled Assertions**: Testing private internals, making refactoring impossible.
6. **Skipping Complexity Check**: High cognitive complexity (>15) means the function needs decomposition.
7. **Mocking Domain Objects**: The domain layer is pure logic. Never mock entities or value objects.
8. **Async Domain Tests**: Domain tests should be sync. Async = architecture smell.
