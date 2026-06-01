## 📋 Descrição do PR

Descreva brevemente o problema resolvido, a motivação e a solução implementada.

- **Bounded Context(s) afetado(s):** `[ex: auth, menu, order, shared]`
- **Tipo de alteração:** `[ex: feat, fix, refactor, test, chore]`
- **Tickets/Issues relacionados:** `Closes #XXX`

---

## 🏛️ Alinhamento de Arquitetura & Boas Práticas

### 🧪 Test-Driven Development (TDD)
- [ ] Escreveu os testes antes do código de produção (RED -> GREEN).
- [ ] commits separados para cada fase (RED, GREEN, REFACTOR, MUTATE).
- [ ] Mutantes mortos ou justificados nas linhas alteradas (Mutation Score = 100%).
- [ ] Testes baseados em propriedades adicionados para lógicas complexas ou de cálculo/estado.

### 🏛️ DDD & Design Patterns
- [ ] Camadas estritamente isoladas (Domínio -> Aplicação -> Infraestrutura -> API).
- [ ] Sem imports de infraestrutura ou I/O no Domínio (SQLAlchemy, Motor, FastAPI).
- [ ] Entidades usam Value Objects imutáveis.
- [ ] Transições de estado delegadas ao Aggregate Root.
- [ ] Eventos de Domínio disparados nas transições corretas.

---

## 🛡️ Checklist de Quality Gates (Validação Local)

Antes de abrir o PR, execute `make hooks` e verifique os seguintes passos:

- [ ] `make fix-back` / `make fix-front` — Código auto-formatado (sem alterações pendentes).
- [ ] `make lint` — Ruff / ESLint rodando com 0 erros.
- [ ] `make typecheck` — Pyright / TypeScript rodando com 0 erros e warnings.
- [ ] `make complexity` — Complexidade cognitiva das funções do backend <= 15.
- [ ] `make test` — Todas as suítes de testes passando (cobertura >= 80%).
- [ ] `make security` — Scanner de segurança executado sem vulnerabilidades de nível alto/crítico.

---

## 📸 Provas Visuais (Para alterações de Frontend/UI)

*Insira capturas de tela ou GIFs que comprovem a alteração visual ou fluxo iterativo (se aplicável).*
