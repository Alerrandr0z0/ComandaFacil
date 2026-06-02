---
name: ai-testing-techniques
description: >
  Guia estratégico e de referência para técnicas avançadas de teste com Inteligência Artificial.
  Abrange Mutation Testing, Property-Based Testing, Fuzzing, visual regression, self-healing tests,
  testes de robustez/segurança para IA (Red-Teaming) e testes metamórficos.
  Use esta skill para orientar estratégias de qualidade avançada, entender limites de mutação,
  lidar com flaky tests e conectar complexidade do código à testabilidade.
---

# Skill: Técnicas Avançadas de Teste com IA — Referência Estratégica

## Visão Geral

Este skill estabelece o referencial teórico e estratégico para a qualidade de software avançada no ecossistema do **ComandaFácil**. Ele funciona como uma enciclopédia de melhores práticas em testes assistidos e direcionados por Inteligência Artificial (AI-driven QA), cobrindo desde a testabilidade do código até a validação de robustez de modelos e sistemas autônomos.

> [!IMPORTANT]
> **Cross-Reference de Workflow Operacional:**
> Para o fluxo operacional pragmático de TDD diário, barreira de qualidade Red-Green-Refactor, comandos locais concretos do Python/TypeScript (como `make mutation-incr`) e regras estritas de commits, consulte a skill [comandafacil-tdd-refactor](file:///home/alerrandro/Desktop/ComandaFacil/.opencode/skills/comandafacil-tdd-refactor/SKILL.md).
> Esta skill (`ai-testing-techniques`) serve como referência estratégica e enciclopédica de alto nível.

---

## Estrutura de Referências

Para aprofundamento operacional e modelos acionáveis, consulte os arquivos sob o diretório `references/`:
- [mutation-testing.md](file:///home/alerrandro/Desktop/ComandaFacil/.opencode/skills/ai-testing-techniques/references/mutation-testing.md) — Estudo aprofundado sobre operadores de mutação, score de mutação na indústria, mutantes equivalentes e integração em CI/CD com `mutmut v3` e `Stryker`.
- [prompts-library.md](file:///home/alerrandro/Desktop/ComandaFacil/.opencode/skills/ai-testing-techniques/references/prompts-library.md) — Biblioteca estruturada de prompts de engenharia de contexto para automação de testes, geração de propriedades, triagem de mutantes equivalentes e análise de flaky tests.

---

## 1. Matriz de Decisão de Técnicas de Teste

Utilize esta matriz para escolher a técnica ideal de acordo com a natureza da funcionalidade e o perfil de risco:

| Técnica | Escopo Principal | Quando Aplicar | Custo Computacional | Retorno (ROI) |
| :--- | :--- | :--- | :--- | :--- |
| **Unitário (Puro)** | Funções isoladas, Value Objects, lógica de domínio pura. | Sempre. Base da pirâmide de testes. | Extremamente Baixo | Alto |
| **Integração (Testcontainers)** | Repositórios Postgres/Mongo, rotas da API, transações físicas. | Interações de I/O, persistência, limites de controllers. | Médio | Alto |
| **Property-Based (PBT)** | Invariantes de estado, algoritmos, serializadores, regras financeiras. | Máquinas de estado de comandas, cálculos de desconto, arredondamento. | Baixo–Médio | Altíssimo (acha edge cases complexos) |
| **Mutation Testing** | Suite de testes existente. | Validação da eficácia dos testes em módulos críticos (auth, payment). | Alto | Alto (evita testes inúteis) |
| **Fuzzing (Adversarial)** | Parsers, inputs de API de rede, upload de arquivos. | Fronteiras expostas à internet, decodificadores de dados. | Altíssimo | Médio–Alto |
| **Visual Regression** | Telas UI, componentes visuais complexos, CSS. | Telas críticas do frontend (Dashboard de Cozinha - KDS). | Médio | Alto (evita layouts quebrados) |
| **Metamorphic Testing** | APIs de Machine Learning, busca semântica, LLMs. | Sistemas cujo output correto é difícil de predizer de forma exata. | Baixo | Alto |

---

## 2. Complexidade como Proxy de Testabilidade

No ComandaFácil, a qualidade dos testes está diretamente ligada à simplicidade estrutural do código. Adotamos uma **abordagem híbrida de controle de complexidade**:

### A Regra Híbrida de Qualidade
- **Complexidade Ciclomática (CC - Caminhos de Decisão)**: Controlada via Ruff regra `C90` (McCabe). O limite máximo permitido para qualquer função é **10**.
  - *Proxy de Testabilidade:* Se a complexidade ciclomática é $M$, o número mínimo de casos de teste necessários para obter 100% de cobertura de caminhos (branch coverage) é de pelo menos $M$ e no máximo $M+1$.
- **Complexidade Cognitiva (Raciocínio Linear)**: Controlada via `complexipy`. O limite máximo permitido é **15**.
  - *Proxy de Testabilidade:* Código com alta complexidade cognitiva (muitos aninhamentos, quebras lógicas consecutivas) é inerentemente confuso para LLMs gerarem casos de teste precisos, além de elevar drasticamente a taxa de falsos negativos.

### Impacto Prático na Automação com IA
LLMs geram asserções de qualidade excepcionalmente alta para funções que respeitam estes limites. Quando a complexidade cognitiva ultrapassa 15:
1. **Refatore Primeiro:** Aplique *Extract Method* ou substitua condicionais complexas por polimorfismo/estratégia antes de acionar a IA para escrever testes.
2. **Decomposição:** Reduza a função em métodos puros e imutáveis, que podem ser facilmente cercados por testes de unidade.

---

## 3. Property-Based Testing com Hypothesis & fast-check

O teste baseado em propriedades (PBT) inverte o fluxo tradicional de testes. Em vez de definir entradas e saídas específicas, define-se **propriedades lógicas invariantes** e permite-se que o framework gere milhares de inputs aleatórios (incluindo valores extremos e boundaries perigosos) para tentar quebrar a lógica.

### Invariantes comuns no ComandaFácil
- **Idempotência:** Executar a operação $N$ vezes resulta no mesmo estado que executá-la uma vez (ex: `cancel_order`).
- **Simetria (Roundtrip):** Converter um objeto para um formato e depois restaurá-lo deve resultar no mesmo objeto original (ex: `to_dict` $\rightarrow$ `from_dict`).
- **Invariante de Estado:** A soma dos valores de todos os itens de uma comanda deve ser sempre igual ao subtotal da comanda, independentemente de cupom aplicado ou alteração de quantidade.

### Organização e Marcação de Testes
Para garantir eficiência na execução da pipeline de CI/CD:
- **Backend (Python - Hypothesis):**
  Todos os testes de propriedade devem usar o marker `@pytest.mark.hypothesis` para permitir isolamento no fluxo de testes rápidos.
  ```python
  import pytest
  from hypothesis import given, strategies as st
  from app.shared.money import Money

  @pytest.mark.hypothesis
  @given(st.decimals(min_value=0.01, max_value=10000.00))
  def test_money_addition_invariant(value: Decimal) -> None:
      # Invariante: x + x = 2x
      m = Money(value)
      assert (m + m).amount == value * 2
  ```
- **Frontend (TypeScript - fast-check):**
  Organizá-los dentro de suítes dedicadas no Vitest para filtragem rápida usando `.property` ou sufixos de arquivo apropriados.

---

## 4. Testes de Integração com Testcontainers

Enquanto os testes unitários são puros e rápidos (executados em milissegundos sem acesso a I/O), o ComandaFácil adota o padrão CQRS (ADR-001) com PostgreSQL para gravação e MongoDB para leitura. Por isso, a fidelidade física na camada de repositório é crucial.

### Arquitetura de Integração
- **Isolamento de Estado:** Utilizamos a biblioteca `testcontainers` para instanciar contêineres Docker leves e descartáveis de PostgreSQL e MongoDB durante a suíte de integração.
- **Conftest Layered:** 
  - `tests/unit/conftest.py` **nunca** importa `app.main` ou inicializa conexões com bancos. Isso garante pureza e velocidade instantânea na execução de testes de domínio puros.
  - `tests/integration/conftest.py` define as fixtures que sobem os contêineres de banco reais, aplicam migrações do Alembic (`alembic upgrade head`) e inicializam o cliente assíncrono do FastAPI (`AsyncClient`).

---

## 5. Flaky Tests — Causa Raiz e Classificação Assistida por IA

Um teste é considerado *flaky* (intermitente) quando ele passa ou falha para o mesmo commit sem alteração no código. Testes flaky destroem a confiança na pipeline de CI/CD e devem ser combatidos rigorosamente.

### As 5 Causas Raiz Comuns
1. **Timing & Asincronismo ( Timing ):** Falta de aguardar promises/tasks assíncronas serem concluídas, utilizando sleeps arbitrários (`time.sleep`) ao invés de estratégias de *polling/wait-until*.
2. **Poluição de Estado Compartilhado ( Shared State ):** Testes que alteram variáveis de escopo global, registros em bancos de dados compartilhados ou mockings globais sem a devida limpeza pós-teste (`tearDown`).
3. **Contenção de Recursos ( Resource Contention ):** Redes lentas, processamento paralelo disputando CPU na máquina de CI, causando estouros de timeout.
4. **Dependência de Ordem ( Ordering Dependency ):** Teste B que só passa se o teste A for executado anteriormente (geralmente por poluição de banco de dados).
5. **Não-determinismo de Ambiente ( Environment ):** Dependência de fuso horário local (`datetime.now()` sem timezone), dependência de ordem do sistema de arquivos ou locale da máquina.

### Triage e Correção Assistida por IA
LLMs são altamente eficazes no diagnóstico de testes flaky ao cruzar o código do teste, o histórico de execuções intermitentes e o log detalhado de falhas no CI. Use a biblioteca de prompts para identificar se o problema é timing ou vazamento de estado global e obter a refatoração exata.

---

## 6. Agentic QA & Context Engineering (2025-2026)

O paradigma de testes evoluiu de **AI-assisted** (onde o desenvolvedor solicita à IA a escrita de um caso de teste simples com base em instruções isoladas) para **Agentic QA (QA Agêntico)** (agentes de software autônomos que planejam, executam, analisam cobertura, buscam lacunas por meio de testes de mutação e reparam o código de forma independente).

### Context Engineering vs. Prompt Engineering
Para que agentes de IA produzam asserções de qualidade industrial, a **Engenharia de Contexto** é infinitamente superior ao simples design de prompts. O contexto deve ser composto por 5 camadas estruturadas:
1. **Contrato do Domínio:** Entidades envolvidas, regras de negócio e invariantes rígidas.
2. **Estrutura de Tipos:** Assinaturas de métodos e schemas completos de dados.
3. **Histórico de Execução:** Stacktraces de falhas anteriores ou relatórios de cobertura.
4. **Linha de Mutação:** O código mutado gerado pelo teste de mutação para demonstrar lacunas na suíte.
5. **Instruções Arquiteturais:** Regras de encapsulamento da aplicação (DDD/ADRs).

---

## 7. Robustez e Testes em Sistemas com LLM (GenAI stack)

Quando o software interage com LLMs ou agentes integrados (como assistentes de atendimento de comandas), os métodos tradicionais de teste falham. É necessário introduzir asserções semânticas e avaliações de robustez:

```
[Entrada Adversarial] ──► [ LLM / Agente ] ──► [ Validador Semântico ] ──► [ Assertions ]
                                                     │
                                            (Relação Metamórfica)
```

### Técnicas Centrais de Robustez
- **Prompts de Red-Teaming (Jailbreaks):** Tentativas ativas de contornar as diretrizes de segurança da IA para induzir alucinações, vazamentos de dados de tenants ou comportamentos inadequados.
- **Relações Metamórficas:** Testes baseados em equivalência semântica de entrada. Se a entrada "Gostaria de uma pizza marguerita para a mesa 4" gera uma comanda correta, a variação "Mesa 4 quer uma pizza marguerita, por favor" deve produzir exatamente o mesmo output estruturado.
- **Golden Datasets:** Uma base estática de 100-200 conversações históricas anotadas manualmente que servem de regressão contínua. Qualquer alteração no prompt do sistema da IA deve ser testada contra o Golden Dataset para garantir que a taxa de acerto semântico não regrida.

---

## Conclusão e Próximos Passos

Esta skill é a base intelectual de qualidade do **ComandaFácil**. Use-a para embasar suas decisões de modelagem de testes e garantir que o ecossistema mantenha barreira de entrada alta contra bugs, regressões estruturais e brechas de segurança.

> [!TIP]
> Consulte a [Biblioteca de Prompts](file:///home/alerrandro/Desktop/ComandaFacil/.opencode/skills/ai-testing-techniques/references/prompts-library.md) sempre que precisar gerar novos testes baseados em propriedades ou diagnosticar falhas intermitentes de forma ágil e precisa.
