---
name: comandafacil-git-workflow
description: >-
  Git Workflow Automation for the ComandaFácil monorepo. Enforces Conventional
  Commits, branch naming conventions, atomic commit discipline per TDD phase,
  and PR checklist templates with quality gate verification.
---

# ComandaFácil — Git Workflow Skill

## Overview

This skill standardizes all Git operations in the ComandaFácil monorepo.
Every branch, commit, and PR follows a predictable pattern that enables
clean history, easy reverts, and automated changelog generation.

**When to activate**: Every time the agent needs to create a branch, write a
commit message, or prepare code for review.

---

## Branch Naming Convention

```
<type>/<context>-<short-description>
```

| Type | When | Example |
|------|------|---------|
| `feat/` | New feature or capability | `feat/auth-jwt-token-generation` |
| `fix/` | Bug fix | `fix/order-total-rounding-error` |
| `refactor/` | Code restructuring (no behavior change) | `refactor/payment-extract-value-objects` |
| `test/` | Test-only changes | `test/menu-property-based-pricing` |
| `chore/` | Tooling, config, dependencies | `chore/backend-upgrade-ruff-rules` |
| `docs/` | Documentation only | `docs/adr-003-event-sourcing` |

**Rules**:
- Context is always the **bounded context name** (`auth`, `menu`, `order`, etc.)
- For cross-cutting changes, use `shared` as context (e.g., `chore/shared-update-base-orm`)
- Use kebab-case, max 50 chars total
- Branch from `main` always

```bash
# Example: starting work on JWT authentication
git checkout main
git pull
git checkout -b feat/auth-jwt-token-generation
```

---

## Conventional Commits

Every commit message MUST follow this format:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Type Reference

| Type | Semântica | Incrementa versão? |
|------|-----------|-------------------|
| `feat` | Nova funcionalidade | MINOR (0.X.0) |
| `fix` | Correção de bug | PATCH (0.0.X) |
| `refactor` | Reestruturação sem mudança de comportamento | — |
| `test` | Adição ou correção de testes | — |
| `docs` | Documentação | — |
| `chore` | Manutenção, tooling, config | — |
| `ci` | CI/CD pipeline | — |
| `perf` | Melhoria de performance | — |
| `style` | Formatação (sem mudança de lógica) | — |

### Scope

Sempre o **bounded context** afetado:

```
feat(auth): implement jwt token generation service
fix(order): correct decimal rounding in total calculation
refactor(payment): extract Money value object
test(menu): add property-based test for price calculation
chore(shared): upgrade sqlalchemy to 2.1
```

### Breaking Changes

Use `!` após o tipo ou adicione `BREAKING CHANGE:` no footer:

```
feat(auth)!: change token payload structure

BREAKING CHANGE: JWT payload now includes `franchise_id` field.
All existing tokens will be invalidated.
```

---

## TDD Phase Commits

During a TDD cycle, commits follow this precise sequence:

```
Phase 1 (RED):
  test(auth): add failing test for jwt token expiry validation

Phase 2 (GREEN):
  feat(auth): implement jwt token expiry validation

Phase 3 (REFACTOR):
  refactor(auth): extract token config to dedicated value object

Phase 4 (MUTATE — if new tests added):
  test(auth): kill surviving mutant in token expiry boundary check
```

**Rules**:
- Each phase gets its own commit — never squash RED + GREEN into one.
- The RED commit contains ONLY the test file(s).
- The GREEN commit contains ONLY the production code.
- The REFACTOR commit may touch both test and production code.

---

## Commit Message Generation

When generating a commit message from a diff, follow this algorithm:

1. **Identify changed files**: Map them to their bounded context.
2. **Classify the change type**: Is it a new feature, fix, refactor, or test?
3. **Write the subject line**: `<type>(<scope>): <imperative verb> <what>`
   - Use imperative mood: "add", "fix", "extract", "remove" (not "added", "fixes")
   - Max 72 characters
   - No period at the end
4. **Add body if needed**: Explain *why*, not *what* (the diff shows what).

### Examples

```bash
# Simple feature
git commit -m "feat(auth): implement password hashing with bcrypt"

# Fix with explanation
git commit -m "fix(order): correct total calculation for zero-quantity items

Previously, items with quantity=0 were included in the total sum,
causing incorrect pricing. Now filtered before calculation."

# Refactor
git commit -m "refactor(stock): replace global state with dependency injection"
```

---

## PR Checklist Template

When preparing a PR or summarizing completed work, include this checklist:

```markdown
## PR Checklist — ComandaFácil

### Quality Gates
- [ ] `make fix-back` — Auto-formatted (0 changes remaining)
- [ ] `uv run ruff check .` — 0 errors
- [ ] `uv run pyright` — 0 errors, 0 warnings
- [ ] `uv run complexipy app/{context}/ --max-complexity-allowed 15` — All functions ≤ 15
- [ ] `uv run pytest tests/ -v` — All tests green
- [ ] `uv run bandit -r app/{context}/ -s B101 -ll` — No high/critical findings

### TDD Discipline
- [ ] Every production function has at least one corresponding test
- [ ] Property-based tests exist for calculations/state machines
- [ ] Mutation score = 100% on modified lines

### DDD Architecture
- [ ] No cross-context imports
- [ ] Domain layer has zero I/O imports (no sqlalchemy, motor, fastapi)
- [ ] Value Objects are frozen (immutable)
- [ ] State changes go through Aggregate Root
- [ ] Domain Events emitted on state transitions

### Git Hygiene
- [ ] Branch follows naming convention: `<type>/<context>-<description>`
- [ ] All commits follow Conventional Commits format
- [ ] RED/GREEN/REFACTOR commits are separate (not squashed)
```

---

## Protected Branch Rules

| Branch | Who can push | Requirements |
|--------|-------------|--------------|
| `main` | Nobody (PR only) | CI/CD pipeline green, GitHub PR checklist completed, 1 approval |
| `feat/*`, `fix/*` | Agent + Developer | Commits follow convention, no force-pushes allowed without coordination |
| `release/*` | Maintainer only | All tests + mutation green |

---

## GitHub Integration & Automation

### 1. GitHub Pull Request Template
The monorepo contains a standard template at [pull_request_template.md](file:///home/alerrandro/Desktop/ComandaFacil/.github/pull_request_template.md).
Every Pull Request created on GitHub will automatically render this checklist. The agent/developer MUST check all boxes before requesting review.

### 2. CI/CD Pipeline (GitHub Actions)
The workflow defined at [ci.yml](file:///home/alerrandro/Desktop/ComandaFacil/.github/workflows/ci.yml) runs automatically on every Push and Pull Request targeting `main`. It verifies:
- **Linter & Formatter**: Ruff check and Ruff format verification.
- **Type Safety**: Full Pyright typechecking.
- **Complexity**: `complexipy` scanning (Cognitive Complexity ≤ 15).
- **Security**: `bandit` scan and dependency audit.
- **Test Suite**: Fully executes pytest with minimum coverage of 80%.

---

## GitHub Merge Strategy: Rebase & Merge

> [!IMPORTANT]
> **DO NOT use Squash & Merge!**
> Squashing compresses all commits into one single commit before merging. This completely destroys the granular TDD history (RED -> GREEN -> REFACTOR -> MUTATE) that we painstakingly created.

### Allowed Merge Strategies:
1. **Rebase & Merge (Recommended)**: Preserves the exact commits of the TDD cycle linearly on `main` without creating merge commits.
2. **Create a Merge Commit**: Preserves the individual commits and keeps them grouped inside a merge bubble.

---

## Semantic Releases & Changelog Automation

By enforcing Conventional Commits, we enable **Automated Releases** (via `release-please` or `semantic-release`).

### How it works:
1. When a PR is merged into `main` using Conventional Commits, the release tool parses the commit types.
2. If it finds a `feat(...)` commit, it bumps the **minor** version (`0.1.0` -> `0.2.0`).
3. If it finds a `fix(...)` commit, it bumps the **patch** version (`0.1.0` -> `0.1.1`).
4. If a commit contains a `BREAKING CHANGE:` footer or `!`, it bumps the **major** version (`1.0.0` -> `2.0.0`).
5. A `release-please` bot automatically creates a PR on GitHub updating `CHANGELOG.md` and drafting a new GitHub Release with the list of changes categorized by context.

---

## Common Mistakes

1. **Squashing TDD phases**: Combining RED + GREEN into one commit loses the audit trail of what was tested before implementation.
2. **Using Squash & Merge on GitHub**: Destroys the valuable granular commit history on the `main` branch.
3. **Vague commit messages**: `"fix stuff"` or `"update code"` — always use Conventional Commits with scope.
4. **Wrong type**: Using `feat` for a refactor, or `fix` for a new feature. The type affects versioning.
5. **Missing scope**: `feat: add token` — always specify the bounded context.
6. **Non-imperative mood**: `"added validation"` → use `"add validation"`.
