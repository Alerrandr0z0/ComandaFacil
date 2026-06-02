# ComandaFácil — Frontend

SPA para gestão de comandas em restaurantes.

## Stack

- **Framework:** React 19 + Vite 8 + TypeScript 6
- **Estilo:** Tailwind CSS 4 (design system custom dark)
- **Estado:** TanStack React Query + React Context
- **HTTP:** Axios
- **Ícones:** Lucide React
- **Gráficos:** Recharts
- **Testes:** Vitest + Playwright + MSW + fast-check

## Features

| Contexto | Componente | Descrição |
|----------|-----------|-----------|
| `auth` | `AuthContext` | Login/logout stateful com session + X-Tenant-ID |
| `menu` | `CatalogViewer` | Cardápio com busca e filtro por categoria |
| `order` | `TableGrid` + `OrderDraft` | Mapa de mesas + lançamento de itens |
| `kitchen` | `KdsBoard` | Kanban em tempo real via WebSocket |
| `payment` | `CheckoutFlow` | Fluxo 3 passos (PIX/Card/Cash) |
| `stock` | `StockManager` | CRUD de estoque com alertas |
| `analytics` | `AnalyticsDashboard` | KPIs com gráficos Recharts |

## Páginas

| Rota | Página | Autenticada |
|------|--------|:-----------:|
| `/login` | Login | ❌ |
| `/orders` | Comandas (mesas + pedidos + checkout) | ✅ |
| `/kitchen` | KDS (cozinha) | ✅ |
| `/stock` | Estoque | ✅ |
| `/analytics` | Dashboard | ✅ |

## Comandos

| Comando | Descrição |
|---------|-----------|
| `npm run dev` | Dev server (HMR) |
| `npm run lint` | Biome check |
| `npm run fix` | Biome autofix |
| `npm run typecheck` | tsc --noEmit |
| `npm run test` | Vitest |
| `npm run test:mutation` | Stryker |
| `npm run e2e` | Playwright |

## Multi-tenancy

Autenticação stateful (session-based, sem JWT stateless). Tenant ID via header `X-Tenant-ID`. Gerenciado pelo `TenantProvider` + interceptor Axios.
