# ADR 002 — Centralização de Logs em Stdout com Metadados de Tenant

**Status:** Superado (Supercedido pelo modelo Cloud-Native)  
**Data:** 2026-06-02

## Contexto

A decisão anterior de salvar logs fisicamente em arquivos segmentados por franquia (`logs/franquias/<tenant_id>/app.log`) no servidor VPS apresentava três falhas graves identificadas durante o desenvolvimento:
1. **Risco de Segurança (Path Traversal):** O valor de `tenant_id` fornecido pelo cabeçalho `X-Tenant-ID` era concatenado diretamente ao caminho de arquivos. Um cabeçalho malicioso como `../../../../etc` permitia a criação e escrita de arquivos fora do diretório do projeto.
2. **Vazamento de Recursos (File Descriptors):** A criação dinâmica e retenção de instâncias de `TimedRotatingFileHandler` para cada franquia causava o acúmulo de arquivos abertos. Sob concorrência elevada, isso causaria a queda da aplicação por limite excedido do SO (`EMFILE: Too many open files`).
3. **Performance (Bloqueio de I/O):** Gravações físicas e síncronas de arquivos no disco durante o ciclo de requisição bloqueavam a Event Loop assíncrona do FastAPI/Uvicorn, degradando a latência sob concorrência.
4. **Acoplamento do Reloader:** Durante o desenvolvimento local, escritas contínuas nos arquivos de log dentro do diretório do projeto geravam falso-positivos no monitor de arquivos, causando loops de reinicialização infinita (hot-reload loop).

## Decisão

1. **Stdout Centralizado:** Removemos a escrita física direta em arquivos (`TenantFileRouter`). Todo o fluxo de logs estruturados em JSON é enviado exclusivamente para a saída padrão (`stdout`) da aplicação.
2. **Metadados de Tenant:** O formatador `TenantAwareJsonFormatter` mantém a injeção do atributo `"tenant_id"` em cada linha JSON de log. Em ambiente de produção, ferramentas externas de gerenciamento e coleta de logs (como Grafana Loki, FluentBit, Vector, Promtail) indexarão e filtrarão os logs por tenant em tempo real, sem nenhum impacto de performance ou gerenciamento de disco na aplicação.
3. **Sanitização de Input:** O cabeçalho `X-Tenant-ID` é sanitizado no middleware principal usando a expressão regular `^[a-zA-Z0-9_-]+$`. Qualquer caractere de path traversal (como `.` ou `/`) ou injeção é rejeitado imediatamente com erro `400 Bad Request`.

## Consequências

- **Segurança:** 100% livre de Path Traversal na gestão de franquias.
- **Performance:** 0% de latência de bloqueio de escrita física de logs na Thread principal da aplicação.
- **Conformidade Cloud-Native:** Alinhado com as diretrizes do Twelve-Factor App (Logs como streams de eventos).
