---
marp: true
theme: default
paginate: true
header: 'Estudo de Caso: Arquitetura de Dados no ComandaFacil'
footer: 'Disciplina de Banco de Dados'
style: |
  section {
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
  }
  h1 { color: #2c3e50; }
  h2 { color: #34495e; border-bottom: 2px solid #ecf0f1; padding-bottom: 5px; }
  .small-text { font-size: 0.8em; }
  .highlight { color: #e74c3c; font-weight: bold; }
---

# Banco de Dados em Sistemas de Missão Crítica
## Um Estudo de Caso da Arquitetura do Sistema **ComandaFacil**

---

## 1. O Problema: Conflito de Cargas de Trabalho (Workloads)

Sistemas tradicionais frequentemente sofrem ao tentar equilibrar duas necessidades conflitantes no mesmo banco de dados:

1. **Escrita Segura (OLTP):** Um garçom registra um pedido. A transação precisa ser **ACID**. Se a internet cair no meio, o pedido não pode ser salvo pela metade.
2. **Leitura Rápida (OLAP/Read-heavy):** Um cliente abre o cardápio. Um gerente abre o dashboard. Essas operações exigem leitura de dados pesados e agregações complexas, o que **bloqueia** as tabelas de escrita.

*Como escalar sem que uma leitura pesada de relatórios trave o registro de novos pedidos em horário de pico?*

---

## 2. CQRS: Por que separar?

A arquitetura adota o padrão **CQRS** (Command Query Responsibility Segregation). 

### Justificativas Estratégicas:
- **Isolamento de Performance:** Uma consulta lenta de analytics no MongoDB nunca bloqueia uma inserção de pedido no PostgreSQL.
- **Modelagem Especializada:** No Postgres, os dados são normalizados para evitar duplicidade. No Mongo, os dados são desnormalizados para evitar JOINs.
- **Escalabilidade Independente:** Podemos aumentar o servidor de leitura (Mongo) sem mexer no servidor de escrita, economizando custos.

---

## 3. Persistência Poliglota na Prática

| Característica | Write DB (A Fonte da Verdade) | Read DB (O Motor de Performance) |
| :--- | :--- | :--- |
| **Tecnologia** | PostgreSQL (Relacional) | MongoDB (NoSQL Document Store) |
| **Foco** | Consistência, Integridade, ACID | Velocidade, Agregações, Performance |
| **Modelagem** | Normalizada (3NF) | Desnormalizada (Read Models) |
| **Garantia** | Integridade Referencial (FKs) | Leituras O(1) sem JOINs |

---

## 4. O Lado da Escrita: PostgreSQL

O PostgreSQL é o coração transacional. Ele garante que as regras de negócio sejam respeitadas através de transações.

- **Integridade:** Se um pedido é criado e o estoque é deduzido, ambas as operações são atômicas.
- **Estrutura Relacional:**
  - `menus` (1) : (N) `menu_items`
  - `stock_items` (1) : (N) `transactions`
- **Consistência Forte:** O sistema nunca permite "vender o que não existe" ou "perder um pagamento" por falha de banco.

---

## 5. O Lado da Leitura: MongoDB (Read Models)

O MongoDB atua como uma **Materialized View** viva.

**Vantagem Técnica:** Em vez de unir 5 tabelas (Menu, Categoria, Item, Preço, Promoção) via SQL, o sistema lê um único documento JSON pronto.

**Exemplo de Documento (`menu_read_models`):**
```json
{
  "menu_id": 1,
  "tenant_id": "franquia_01",
  "items": [
    { "name": "Hambúrguer", "price": 28.90, "category": "Lanches" }
  ]
}
```
*Tempo de resposta: < 5ms (mesmo com milhões de itens).*

---

## 6. A Ponte de Confiança: Outbox Pattern

Manter dois bancos exige uma sincronização infalível. Não podemos salvar no Postgres e "torcer" para que o Mongo seja atualizado.

### O Problema: "Dual Writes"
Se o app salva no Postgres e cai antes de salvar no Mongo, os bancos ficam dessincronizados.

### A Solução: Padrão Outbox
1. Dentro da **mesma transação** do pedido no Postgres, o app salva uma mensagem na tabela `outbox`.
2. Um processo separado (Worker) lê essa tabela e envia para o MongoDB.
3. Se o Worker falhar, ele tenta novamente até o MongoDB confirmar o recebimento.
*Resultado: Garantia de que o Mongo será atualizado, mesmo após falhas de rede.*

---

## 7. Multi-tenancy: O Modelo SaaS

O sistema atende milhares de restaurantes na mesma infraestrutura.

### Por que Multitenant?
- **Economia de Escala:** Um único cluster de banco de dados atende todos os clientes.
- **Manutenção Unificada:** Uma única migração de schema atualiza todos os restaurantes simultaneamente.

### Segurança e Isolamento:
- **Identidade Lógica:** Cada linha no Postgres e cada documento no Mongo possui um `tenant_id`.
- **Filtro Automático:** O sistema injeta `WHERE tenant_id = 'X'` em todas as queries, garantindo que um restaurante nunca acesse dados de outro.

---

## 8. Analytics (O Poder do NoSQL)

O MongoDB permite agregar dados entre contextos sem esforço.

**Exemplo: Tempo médio de preparo por estação**
```json
[
  {"$match": {"tenant_id": "franquia_01", "state": "READY"}},
  {"$project": {"time": {"$subtract": ["$completed_at", "$started_at"]}}},
  {"$group": {"_id": "$station", "avg_time": {"$avg": "$time"}}}
]
```
No PostgreSQL, essa query exigiria scans pesados em tabelas de histórico. No MongoDB, os dados já estão estruturados para essa análise.

---

## 9. Conclusão

A arquitetura do ComandaFacil usa o que há de mais moderno em engenharia de dados:

1. **CQRS:** Para performance extrema e isolamento de carga.
2. **Outbox Pattern:** Para garantir que a sincronização entre bancos nunca falhe.
3. **Multi-tenancy:** Para escala comercial massiva (SaaS).
4. **Persistência Poliglota:** Cada ferramenta (SQL e NoSQL) faz o que faz de melhor.

**"O banco de dados perfeito não existe; o que existe é a combinação certa para cada necessidade."**
