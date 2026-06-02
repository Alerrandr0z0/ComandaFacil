---
name: mutation-testing
description: >
  Referência completa de teste de mutação — operadores, métricas, ferramentas
  (mutmut v3, Stryker), mutantes equivalentes e estratégia de CI/CD em camadas.
---

# Teste de Mutação — Referência

Teste de mutação mede a **qualidade** da suíte de testes, não a cobertura de código.
Um *mutante* é uma cópia do código-fonte com uma micro-alteração sintática.
Se nenhum teste falha, o mutante **sobreviveu** — há uma lacuna na suíte.

---

## 1. Operadores de Mutação Clássicos

| Categoria | Operador | Exemplo original → mutante |
|-----------|----------|---------------------------|
| Relacional | `==` → `!=` | `if x == 0` → `if x != 0` |
| Relacional | `<` → `<=` | `if x < 10` → `if x <= 10` |
| Relacional | `>` → `>=` | `if x > 0` → `if x >= 0` |
| Aritmético | `+` → `-` | `total + taxa` → `total - taxa` |
| Aritmético | `*` → `/` | `preco * qtd` → `preco / qtd` |
| Aritmético | `%` → `*` | `i % 2` → `i * 2` |
| Lógico | `and` → `or` | `a and b` → `a or b` |
| Lógico | `not x` → `x` | `not is_valid` → `is_valid` |
| Valor | `0` → `1` | `return 0` → `return 1` |
| Valor | `""` → `"mutant"` | `msg = ""` → `msg = "mutant"` |
| Valor | `True` → `False` | `flag = True` → `flag = False` |
| Controle | remove `else` | bloco `else` inteiro removido |
| Controle | `break` → `continue` | loop `break` → `continue` |
| Controle | remove chamada | `validate(x)` → *(removido)* |

---

## 2. Mutation Score

```
Mutation Score = mutantes mortos / (total de mutantes − equivalentes) × 100
```

### Escala de interpretação

| Faixa | Classificação | Orientação |
|-------|---------------|------------|
| < 50% | Muito fraca | CI deve quebrar. Testes provavelmente são superficiais. |
| 50–70% | Aceitável | Adequado para código não-crítico ou módulos estáveis. |
| 70–80% | Bom | **Sweet spot da indústria** — plateau natural (Google, Meta). |
| 80–90% | Excelente | Recomendado para módulos críticos: `auth`, `payment`, `health`. |
| > 90% | Excepcional | Raramente sustentável. ~40% dos sobreviventes podem ser equivalentes. |

> **Nota:** Exigir 100% é irrealista — mutantes equivalentes são matematicamente
> indecidíveis (problema redutível ao Halting Problem) e podem representar até 40%
> dos sobreviventes em bases reais.

---

## 3. Mutantes Equivalentes

Um mutante equivalente produz **comportamento idêntico** ao original para todas
as entradas possíveis. Exemplos comuns:

```python
# Original
def clamp(x: int) -> int:
    return max(0, min(x, 100))

# Mutante equivalente — max(0, min(x, 100)) == max(min(x, 100), 0)
def clamp(x: int) -> int:
    return max(min(x, 100), 0)
```

**Por que importam:** inflam falsos negativos no mutation score. Dedicar tempo
matando equivalentes é desperdício — marque-os e siga em frente.

### Estratégias de detecção

| Técnica | Custo | Precisão |
|---------|-------|----------|
| Inspeção manual | Alto | Alta |
| Análise estática (TCE) | Baixo | Moderada |
| Geração de contra-exemplos (SMT) | Médio | Alta |
| Triagem assistida por LLM | Baixo | Moderada–Alta |

---

## 4. Seleção Inteligente de Mutantes

Executar todos os mutantes é proibitivo em bases grandes. Técnicas de redução:

- **Amostragem aleatória:** selecionar X% dos mutantes por arquivo.
- **Mutação incremental:** mutar apenas arquivos alterados no diff (ideal para CI).
- **Operadores seletivos:** usar apenas 5–7 operadores mais eficazes (pesquisa de
  Offutt 1996: 5 operadores suficientes capturam ~99% dos defeitos).
- **Mutação de primeira ordem (FOM):** uma mutação por vez, evitar combinatórias.
- **Priorização por cobertura:** mutar apenas linhas cobertas por testes existentes.

---

## 5. Integração com CI/CD — Stryker (JS/TS)

```json
// stryker.conf.json
{
  "mutate": ["src/**/*.ts", "!src/**/*.spec.ts"],
  "testRunner": "vitest",
  "reporters": ["html", "dashboard", "progress"],
  "thresholds": { "high": 80, "low": 60, "break": 60 },
  "incremental": true,
  "incrementalFile": "reports/stryker-incremental.json"
}
```

- `--since main` → muta apenas arquivos alterados em relação a `main`.
- `thresholds.break` → CI falha se o score ficar abaixo desse valor.
- `incremental: true` → reutiliza resultados anteriores para acelerar re-runs.

---

## 6. mutmut v3 (Python)

mutmut v3 **não aceita flags CLI** para paths — toda configuração fica no
`pyproject.toml`:

```toml
[tool.mutmut]
paths_to_mutate = "app/"
tests_dir = "tests/"
also_copy = ["alembic/", "alembic.ini"]
```

| Campo | Descrição |
|-------|-----------|
| `paths_to_mutate` | Diretórios a serem mutados. |
| `tests_dir` | Diretório de testes a executar contra cada mutante. |
| `also_copy` | Arquivos/diretórios fora do escopo de mutação que os testes precisam. |

### Comandos principais

```bash
# Execução completa (4 workers paralelos)
mutmut run --max-children 4

# Visualizar sobreviventes
mutmut results

# Detalhes de um mutante específico
mutmut show <id>

# Aplicar mutante para análise manual
mutmut apply <id>
```

### Mutação incremental

Para mutar apenas um contexto (ex.: `order`), sobrescreva temporariamente no
`pyproject.toml` ou use o target do Makefile:

```bash
make mutation-incr PATHS='app/order/' TESTS='tests/unit/order/'
```

> O target `mutation-incr` ajusta `paths_to_mutate` e `tests_dir` via `sed`,
> executa `mutmut run`, e restaura o `pyproject.toml` original.

---

## 7. Mutantes Equivalentes + LLM

LLMs conseguem **raciocinar semanticamente** sobre equivalência — algo que análise
estática tradicional não faz bem. Aplicações práticas:

1. **Triagem de sobreviventes:** enviar o diff do mutante + código ao redor para a
   LLM classificar como equivalente/não-equivalente com justificativa.
2. **Sugestão de teste matador:** para não-equivalentes, a LLM pode sugerir um
   caso de teste que exponha a mutação.
3. **Revisão incremental (modelo Google):** mutação aplicada durante code review —
   cada mutante aparece como comentário inline no PR. Limita carga cognitiva ao
   delta do commit.

### Referência

> *"An Industrial Application of Mutation Testing"* — Google, 2018. Mutação
> incremental durante code review capturou defeitos reais com overhead aceitável.
> Mutantes equivalentes são marcados e ignorados em iterações futuras.

**Estratégia prática:** marque como equivalente → registre no relatório → foque
nos sobreviventes não-equivalentes. Não perca tempo tentando matar o que não
pode morrer.

---

## 8. Estratégia de CI/CD em Camadas

Nem toda mutação precisa rodar em todo push. Estruture em camadas:

```
on_push_to_feature:     fast     → unit tests + coverage only
on_PR_to_main:          medium   → + mutation incremental (só arquivos mudados)
nightly / weekly:       full     → mutation testing completo
```

### Implementação por stack

| Evento | Python (mutmut) | JS/TS (Stryker) |
|--------|-----------------|-----------------|
| Push feature | `pytest --cov` | `vitest --coverage` |
| PR → main | `make mutation-incr PATHS='...' TESTS='...'` | `stryker run --since main` |
| Nightly | `mutmut run --max-children 4` | `stryker run` (full) |

### Vantagens

- **Push rápido** (~30s): não bloqueia fluxo do dev.
- **PR com mutação incremental** (~2–5min): detecta lacunas no delta.
- **Nightly completo** (~15–60min): baseline atualizado para tendências.

---

## Referências

- Jia, Y. & Harman, M. (2011). *An Analysis and Survey of the Development of
  Mutation Testing.* IEEE TSE, 37(5).
- Offutt, A.J. et al. (1996). *An Experimental Determination of Sufficient
  Mutant Operators.* ACM TOSEM, 5(2).
- Petrovic, G. & Ivankovic, M. (2018). *State of Mutation Testing at Google.*
  ICSE-SEIP.
- mutmut docs: https://mutmut.readthedocs.io/
- Stryker docs: https://stryker-mutator.io/docs/
