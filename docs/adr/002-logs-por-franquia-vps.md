# ADR 002 — Logs Físicos Segmentados por Franquia (VPS)

**Status:** Aceito
**Data:** 2026-06-01

## Contexto

O sistema será hospedado em uma VPS tradicional (não containerizada para produção inicial). É necessário rastrear e auditar ações por franquia de forma isolada.

## Decisão

Logs físicos em arquivos, segmentados por pasta de franquia, usando `TimedRotatingFileHandler` do Python:

```
logs/
└── franquias/
    ├── franquia_001/
    │   └── app.log   ← rotacionado diariamente, 30 dias de retenção
    └── franquia_002/
        └── app.log
```

O `tenant_id` da requisição é extraído via middleware e injetado no `ContextVar` do `TenantContext`. O `LoggingMiddleware` usa esse contexto para direcionar a gravação ao arquivo correto.

## Formato do Log

JSON estruturado para facilitar análise futura:
```json
{"timestamp": "2026-06-01T20:00:00Z", "level": "INFO", "tenant_id": "franquia_001", "message": "Pedido criado", "order_id": 42}
```

## Tradeoffs

- ✅ Isolamento por franquia (LGPD, suporte, auditoria)
- ✅ Sem dependências externas (simples na VPS)
- ⚠️ Análise global requer varredura de múltiplos arquivos (aceitável no curto prazo)
- ⚠️ Incompatível com containers stateless (migração futura para stdout + Loki se necessário)
