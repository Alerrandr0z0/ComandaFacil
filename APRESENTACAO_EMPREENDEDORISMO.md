# Apresentação — ComandaFácil: Empreendedorismo & Gestão Estratégica

---

## Contexto SWOT do ComandaFácil

### Forças
- Tecnologia própria com arquitetura moderna (DDD + CQRS + multi-tenancy)
- Cobertura completa do fluxo do restaurante: menu → pedido → cozinha → pagamento → estoque → analytics
- Interface Web (sem instalação) com KDS em tempo real via WebSocket
- Código-fonte com altíssima qualidade técnica (255 testes, 88% cobertura, CI automatizado)
- Modelo multi-tenant: um software atende vários restaurantes simultaneamente

### Fraquezas
- Pouco capital para marketing e vendas
- Equipe pequena (desenvolvimento inicial)
- Marca desconhecida no mercado
- Produto ainda sem validação em larga escala
- Dependência de internet estável (sem modo offline)

### Oportunidades
- Crescimento da digitalização de restaurantes no Brasil pós-pandemia
- Pequenos e médios restaurantes em Tibau/RN carecem de soluções acessíveis
- Turismo sazonal em Tibau gera demanda por eficiência operacional
- Expansão gradual para cidades vizinhas (Costa Branca → Natal → estados vizinhos → Nordeste)
- Grandes players (iFood, Linx) têm preços altos para pequenos estabelecimentos

### Ameaças
- Grandes players entrando no mercado de gestão para pequenos restaurantes
- Concorrentes com mais verba de marketing e vendas
- Resistência de donos de restaurantes à tecnologia
- Variação cambial afetando custos de infraestrutura em nuvem

---

## Nível Estratégico (3 anos)

- **Objetivo E1:** Alcançar 30% de participação nos restaurantes de Tibau/RN e expandir para toda a Costa Branca (Areia Branca, Grossos, Porto do Mangue).
- **Objetivo E2:** Tornar-se referência em gestão de quiosques e restaurantes no Rio Grande do Norte, mantendo NPS ≥ 85 e uptime ≥ 99,5%.
- **Objetivo E3:** Consolidar presença em Natal/RN e iniciar operação em estados vizinhos (Paraíba, Pernambuco, Ceará).

---

## Nível Tático (1–2 anos, por área)

### Marketing

- **Meta T1-MKT:** Atingir 50 restaurantes cadastrados na plataforma em 18 meses.
- **Ações táticas principais:**
  - Campanhas digitais segmentadas por raio de 10 km em Tibau e Costa Branca.
  - Parcerias com 10 restaurantes âncora em Tibau como vitrine do produto.
  - Programa "Indique e Ganhe" para restaurantes usuários indicarem outros.
  - Presença em feiras e eventos gastronômicos regionais.

### Operações

- **Meta T1-OPS:** Garantir onboarding de novos restaurantes em até 48 horas com suporte dedicado.
- **Meta T2-OPS:** Manter tempo médio de suporte técnico < 4 horas úteis.
- **Ações táticas principais:**
  - Criar materiais de treinamento e onboarding autoguiado.
  - Estabelecer canal de suporte via WhatsApp Business.
  - Contratar suporte técnico regional para expansão em Natal.

### Produto/TI

- **Meta T1-TI:** Garantir 99,5% de disponibilidade do sistema e suportar 1.000 pedidos simultâneos.
- **Meta T2-TI:** Implementar funcionalidades de pagamento integrado (maquininha via API) em até 12 meses.
- **Ações táticas principais:**
  - Refatorar backend para escalabilidade horizontal.
  - Implementar monitoramento e alertas (APM, logging estruturado).
  - Adicionar modo offline para operações em áreas com internet instável.
  - Desenvolver app mobile para garçons e cozinha.

---

## Nível Operacional — Plano dos Próximos 90 Dias

### Marketing – Plano Operacional

| Tarefa | Descrição | Responsável | Prazo |
|--------|-----------|-------------|-------|
| O1 | Visitar 2 restaurantes por semana em Tibau para apresentar o produto e fechar parcerias | Comercial | Imediato; meta de 8 parcerias em 60 dias |
| O2 | Criar perfil do ComandaFácil no Instagram e Facebook com conteúdo semanal (cases, dicas) | Analista de marketing | 15 dias |
| O3 | Produzir material de divulgação impresso (panfletos, cartões) para distribuição local | Analista de marketing | 30 dias |
| O4 | Registrar 3 restaurantes-âncora para uso gratuito como vitrine | Comercial | 45 dias |

### Produto/TI – Plano Operacional

| Tarefa | Descrição | Responsável | Prazo |
|--------|-----------|-------------|-------|
| O5 | Configurar monitoramento de disponibilidade e alertas de erro | Squad de TI | 2 semanas |
| O6 | Realizar testes de usabilidade com 3 restaurantes piloto em Tibau | Squad de produto | 30 dias |
| O7 | Coletar e priorizar feedback dos pilotos para o backlog | PO + squad | 45 dias |
| O8 | Implementar melhorias críticas apontadas nos pilotos | Squad de produto | 60–90 dias |
| O9 | Criar dashboard de analytics para donos de restaurante (faturamento, pedidos, ticket médio) | Squad de produto | 90 dias |

### Operações – Plano Operacional

| Tarefa | Descrição | Responsável | Prazo |
|--------|-----------|-------------|-------|
| O10 | Mapear restaurantes de Tibau por segmento (quiosque, pizzaria, lanchonete, restaurante) | Comercial | 30 dias |
| O11 | Criar material de treinamento (vídeos curtos + PDF) para onboarding | Squad de produto | 45 dias |
| O12 | Definir precificação e planos (mensalidade + taxa por pedido) | PO + comercial | 30 dias |

---

## Abordagens Ágeis

| Abordagem | Foco principal | Características | Quando usar |
|-----------|---------------|-----------------|-------------|
| **Scrum** | Gestão iterativa do trabalho | Sprints, backlog e papéis definidos | Projetos com entregas incrementais e necessidade de organização por ciclos |
| **XP** | Qualidade técnica do software | TDD, programação em par, integração contínua, refatoração e feedback rápido | Quando o projeto exige alta qualidade técnica e adaptação frequente |
| **Kanban** | Fluxo contínuo | Quadro visual, limitação de WIP e melhoria contínua do fluxo | Suporte, manutenção e times com demandas variadas continuamente |
| **Scrumban** | Híbrido de Scrum e Kanban | Combina sprints e planejamento do Scrum com fluxo visual e flexível do Kanban | Times que querem estrutura sem perder flexibilidade operacional |

---

## Papéis no Scrum — ComandaFácil

| Papel | Função principal | Responsabilidades resumidas |
|-------|------------------|-----------------------------|
| **Product Owner (PO)** | Maximizar o valor do produto | Define a visão do produto, prioriza o Product Backlog e decide o que deve ser desenvolvido primeiro |
| **Scrum Master (SM)** | Garantir o bom uso do Scrum | Facilita o processo, remove impedimentos, apoia as cerimônias e ajuda o time a trabalhar melhor |
| **Developers / Equipe de Desenvolvimento** | Construir o incremento do produto | Planejam o trabalho da sprint, desenvolvem, testam, integram e entregam software funcional |

---

## Planejamento Operacional em Scrum — Ciclo Completo

1. **Preparação** — Definir visão do produto, formar equipe, estabelecer backlog, configurar ferramentas
2. **Planejamento do Sprint** — Selecionar itens do backlog para o sprint, definir meta
3. **Execução do Sprint** — Desenvolver com Daily Stand-ups, manter quadro visível
4. **Revisão do Sprint** — Demonstrar o que foi concluído para stakeholders
5. **Retrospectiva do Sprint** — Melhoria contínua do processo
6. **Planejamento do Próximo Sprint** — Reabastecer o backlog, priorizar novamente
7. **Lançamento e Entrega Contínua** — Publicar incrementos em produção

---

## Planejamento Operacional — Preparação

| Atividade | Responsável | Descrição |
|-----------|-------------|-----------|
| Definir a Visão do Produto | PO | "Sistema de gestão de quiosques e restaurantes simples, acessível e completo, começando por Tibau/RN" |
| Formar a Equipe Scrum | Gerente de RH / Founder | PO + SM + 2–3 desenvolvedores + analista de marketing |
| Estabelecer o Backlog do Produto | PO + Stakeholders | Itens priorizados por valor de negócio para os restaurantes piloto |
| Configuração das Ferramentas | Equipe de TI | GitHub, CI/CD, ambiente de produção, monitoramento |

---

## Backlog do Produto — ComandaFácil

| # | Item | Tipo | Descrição curta | Critério de aceite | Responsável |
|---|------|------|-----------------|---------------------|-------------|
| 1 | Onboarding autoguiado para restaurantes | História de usuário | Como dono de restaurante, quero me cadastrar e configurar meu cardápio sozinho para começar a usar rapidamente | Fluxo de cadastro funcional ponta a ponta em até 30 minutos | Squad de produto |
| 2 | Dashboard financeiro para donos | História de usuário | Como dono, quero ver faturamento do dia/mês e ticket médio para acompanhar o negócio | Gráficos com filtro por período; dados atualizados em tempo real | Squad de produto |
| 3 | Relatório de pedidos por período | Tarefa técnica | Como dono, quero exportar relatório de pedidos para prestação de contas | Arquivo CSV/PDF com filtro por data, status e valor | Dev |
| 4 | Integração com maquininha de cartão | História de usuário | Como garçom, quero finalizar pagamento na maquininha sem digitar valor manualmente | Pagamento integrado via API da maquininha; valor enviado automaticamente | Squad de produto |
| 5 | Modo offline para queda de internet | Tarefa técnica | Como garçom, quero continuar anotando pedidos mesmo sem internet | Pedidos salvos localmente e sincronizados quando internet voltar | Dev |
| 6 | Programa de fidelidade para clientes | História de usuário | Como dono, quero oferecer pontos/fidelidade para clientes recorrentes | Pontos acumulados por valor gasto; resgate de brindes configurável | Squad de produto |
| 7 | App mobile para garçons | História de usuário | Como garçom, quero anotar pedidos pelo celular para agilizar o atendimento | App funcional com login, mesas, pedidos e pagamento | Squad de produto |
| 8 | Suporte via WhatsApp integrado | Tarefa técnica | Como dono, quero pedir suporte diretamente pelo sistema | Botão de suporte abre conversa no WhatsApp com dados do restaurante | Dev |
| 9 | Multiusuário por restaurante (gerente + garçons) | História de usuário | Como dono, quero criar contas para meus garçons com permissões limitadas | Perfis de acesso: admin (dono) e operador (garçom) | Squad de produto |
| 10 | Campanha de marketing automatizada (push) | História de usuário | Como dono, quero enviar promoções para clientes cadastrados | Notificação push disparada para clientes com base em regras configuráveis | Squad de produto |

---

## Sprint 1 — Fundação e Piloto em Tibau

- **Duração:** 2 semanas
- **Meta da sprint:** Ter o produto funcional e validado por 3 restaurantes piloto em Tibau, com onboarding e dashboard básico.

### Itens do Sprint 1

**1. Simplificar fluxo de cadastro do restaurante**
- **Tipo:** história de usuário
- **Descrição:** "Como dono de restaurante, quero me cadastrar rapidamente para testar o sistema."
- **Critério de aceite:**
  - Cadastro em até 3 etapas (dados do restaurante → cardápio → teste grátis)
  - Tempo médio de cadastro < 10 minutos
  - Confirmação por e-mail/WhatsApp

**2. Dashboard básico do dono**
- **Tipo:** história de usuário
- **Descrição:** "Como dono, quero ver pedidos do dia e faturamento em uma tela inicial."
- **Critério de aceite:**
  - Cards com: pedidos hoje, faturamento do dia, ticket médio
  - Tabela com últimos pedidos em tempo real

**3. Correção de bugs críticos do piloto anterior**
- **Tipo:** tarefa técnica
- **Descrição:** Corrigir problemas identificados nos testes internos.
- **Critério de aceite:**
  - Bugs que impedem fluxo completo de pedido corrigidos
  - Testes automatizados passando

**4. Criar material de treinamento mínimo**
- **Tipo:** tarefa
- **Descrição:** Produzir vídeo curto (até 5 min) mostrando o fluxo completo.
- **Critério de aceite:**
  - Vídeo publicado no YouTube/privado
  - PDF de 1 página com instruções rápidas

**5. Onboarding de 3 restaurantes piloto**
- **Tipo:** tarefa
- **Descrição:** Visitar, cadastrar e treinar 3 restaurantes em Tibau.
- **Critério de aceite:**
  - 3 restaurantes usando o sistema ativamente
  - Feedback coletado e registrado

---

## Sprint 2 — Monitoramento, Qualidade e Expansão

- **Duração:** 2 semanas
- **Meta da sprint:** Ter o sistema estável com monitoramento, relatório financeiro e preparação para expandir para Costa Branca.

### Itens do Sprint 2

**1. Configurar monitoramento e alertas**
- **Tipo:** tarefa técnica
- **Descrição:** "Como equipe, queremos detectar indisponibilidade e erros rapidamente."
- **Critério de aceite:**
  - Monitoramento de disponibilidade dos endpoints críticos
  - Alertas de erro (5xx, lentidão) configurados
  - Notificações no canal da equipe (e-mail/Slack/WhatsApp)

**2. Relatório financeiro exportável**
- **Tipo:** história de usuário
- **Descrição:** "Como dono, quero exportar relatório de pedidos e faturamento do mês."
- **Critério de aceite:**
  - Relatório em CSV com: data, pedido, itens, valor, forma de pagamento
  - Filtro por período (7, 15, 30 dias)

**3. Melhorias baseadas no feedback dos pilotos**
- **Tipo:** história de usuário
- **Descrição:** Implementar as 3 melhorias mais solicitadas pelos pilotos.
- **Critério de aceite:**
  - Melhorias priorizadas com o PO
  - Implementadas e validadas com os restaurantes

**4. Testes de usabilidade com usuários reais**
- **Tipo:** pesquisa / validação
- **Descrição:** "Como equipe de produto, queremos confirmar se o sistema é intuitivo."
- **Critério de aceite:**
  - Sessões com 3–5 usuários reais (garçons e donos)
  - Principais dificuldades registradas e priorizadas no backlog

**5. Preparar landing page para expansão**
- **Tipo:** tarefa
- **Descrição:** Criar página simples de apresentação do ComandaFácil.
- **Critério de aceite:**
  - Landing page com: benefícios, prints do sistema, formulário de contato
  - Publicada em domínio próprio (ex.: comandafacil.com.br)

---

## Detalhes das Cerimônias

| Cerimônia | Frequência | Duração | Participantes | Objetivo |
|-----------|-----------|---------|---------------|----------|
| **Sprint Planning** | Início de cada sprint | 2h | PO + SM + Devs | Definir o que será trabalhado na sprint |
| **Daily Stand-up** | Diária | 15 min | Toda a equipe de desenvolvimento | Sincronizar atividades e discutir impedimentos |
| **Sprint Review** | Final de cada sprint | 1h | PO + SM + Devs + Stakeholders | Revisar o que foi concluído e demonstrar o trabalho |
| **Sprint Retrospective** | Final de cada sprint | 1h | Toda a equipe de desenvolvimento | Discutir o que funcionou bem e o que pode melhorar |

---

## Resumo

| Nível | Pergunta que responde | Exemplo |
|-------|-----------------------|---------|
| **Estratégico** | "Onde queremos chegar?" | 30% dos restaurantes de Tibau em 3 anos |
| **Tático** | "O que cada área vai fazer?" | Marketing: parcerias com 10 restaurantes âncora |
| **Operacional** | "Quem faz o quê, quando e como?" | Visitar 2 restaurantes por semana em Tibau |
| **Scrum** | "Como organizamos o trabalho?" | Sprints de 2 semanas com backlog priorizado |

---

## Roteiro de Expansão Geográfica

```
Fase 1 (Ano 1): Tibau/RN → Costa Branca
├── Tibau (cidade-base, 3 pilotos)
├── Areia Branca
├── Grossos
└── Porto do Mangue

Fase 2 (Ano 2): Costa Branca → Natal/RN
├── Natal (mercado principal do RN)
├── Parnamirim
└── Extremoz

Fase 3 (Ano 3): RN → Estados vizinhos
├── Paraíba (João Pessoa, Campina Grande)
├── Pernambuco (Recife, Olinda)
├── Ceará (Fortaleza)
└── Alagoas (Maceió)

Fase 4 (Ano 4+): Nordeste
├── Expansão para capitais nordestinas
└── Franquias regionais
```

---

*Documento gerado para fins acadêmicos — Disciplina de Empreendedorismo*
