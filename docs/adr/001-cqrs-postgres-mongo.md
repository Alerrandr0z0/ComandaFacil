# ADR 001 — CQRS: PostgreSQL (Escrita) + MongoDB (Leitura)

**Status:** Aceito
**Data:** 2026-06-01

## Contexto

O ComandaFácil opera no modelo multi-tenant (multi-franquia). Diferentes contextos de uso exigem diferentes características de banco de dados:

- Operações transacionais (pedidos, estoque, pagamentos) exigem consistência ACID.
- Leituras de cardápio por clientes e dashboards de gerentes exigem alta performance com dados pré-agregados.

## Decisão

Adotamos o padrão **CQRS (Command Query Responsibility Segregation)** com dois bancos distintos:

| Responsabilidade | Banco | Justificativa |
|---|---|---|
| **Escrita** (fonte da verdade) | PostgreSQL 16 | ACID, chaves estrangeiras, suporte a migrations |
| **Leitura** (read models) | MongoDB 7 | Documentos JSON desnormalizados, buscas rápidas |

## Dados no MongoDB (Read Models)

- `MenuReadModel` — cardápio completo por tenant (atualizado quando o gerente edita o cardápio)
- `OrderHistoryModel` — pedidos fechados/pagos (imutáveis, nunca alterados após fechamento)
- `AnalyticsModel` — agregados diários/mensais de faturamento e vendas
- `AuditLogsModel` — histórico de ações dos colaboradores por franquia

## Sincronização

Sem Redis. A sincronização é feita via **FastAPI BackgroundTask** disparada após commit bem-sucedido no PostgreSQL.

**Tradeoff aceito:** Se o servidor reiniciar durante uma BackgroundTask, o read model ficará desatualizado até a próxima operação de escrita. Isso é aceitável pois os read models são reconstituíveis a partir do PostgreSQL.

## Consequências

- Cada Bounded Context com necessidade de leitura otimizada terá um `mongo_repository.py` dedicado.
- A camada de API decide de qual banco ler baseada no tipo de operação (query vs command).
