import {
  Activity,
  AlertTriangle,
  Calendar,
  CheckCircle,
  Clock,
  DollarSign,
  Info,
  RefreshCw,
  ShoppingBag,
  Sliders,
  TrendingUp,
  Utensils,
  X,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { httpClient } from '@/shared/lib/http_client'

interface DashboardStats {
  total_sales: string
  orders_count: number
  average_ticket: string
  low_stock_items: number
  average_prep_time_minutes: number
}

interface SalesReport {
  period: string
  total_sales: string
  total_orders: number
  average_ticket: string
  by_category: Record<string, string>
  trends?: { time: string; total: number }[]
}

interface KitchenPerformance {
  period: string
  average_prep_time_minutes: number
  average_queue_time_minutes: number
  items_prepared: number
  completion_rate: number
  by_station?: Record<
    string,
    {
      average_prep_time_minutes: number
      average_queue_time_minutes: number
      items_prepared: number
    }
  >
  sla_compliance_rate: number
  bottlenecks: { name: string; average_prep_time_minutes: number; items_prepared: number }[]
  throughput_trends: { time: string; count: number }[]
  std_dev_prep_time_minutes: number
  queue_vs_prep_trends: { time: string; queue_minutes: number; prep_minutes: number }[]
  waste_cancelled_value: number
  waste_cancelled_count: number
}

interface OrderInsights {
  period: string
  total_orders: number
  average_items_per_order: number
  peak_hour: number
  heatmap?: { day_of_week: number; hour: number; total_sales: number; orders_count: number }[]
}

interface MenuMatrixItem {
  menu_item_id: number
  name: string
  quantity: number
  revenue: number
  avg_price: number
  cost: number
  margin: number
  popularity: 'HIGH' | 'LOW'
  profitability: 'HIGH' | 'LOW'
  classification: 'ELITE' | 'OPORTUNIDADE' | 'ALTO_VOLUME' | 'BAIXO_DESEMPENHO'
  recommendation: string
}

interface MenuMatrixReport {
  items: MenuMatrixItem[]
  average_quantity: number
  average_margin: number
}

interface DemandForecast {
  time: string
  total: number
}

interface OrderFunnel {
  avg_queue_minutes: number
  avg_prep_minutes: number
  avg_checkout_minutes: number
  avg_total_cycle_minutes: number
}

interface TablePerformance {
  table_number: number
  total_revenue: number
  orders_count: number
  avg_ticket: number
}

interface ComboRecommendation {
  item_a: string
  item_b: string
  co_occurrences: number
  support: number
  confidence_a_to_b: number
  confidence_b_to_a: number
}

interface CannibalizationWarning {
  category: string
  cannibalized_item_name: string
  cannibalized_item_id: number
  cannibalized_drop: number
  cannibalized_pct: number
  growing_item_name: string
  growing_item_id: number
  growing_rise: number
  growing_pct: number
  confidence: 'HIGH' | 'MEDIUM'
}
interface MenuMatrixTableRowProps {
  item: MenuMatrixItem
}

function MenuMatrixTableRow({ item }: MenuMatrixTableRowProps) {
  let badgeStyle = ''
  if (item.classification === 'ELITE') {
    badgeStyle = 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
  } else if (item.classification === 'OPORTUNIDADE') {
    badgeStyle = 'bg-brand-500/10 text-brand-400 border border-brand-500/20'
  } else if (item.classification === 'ALTO_VOLUME') {
    badgeStyle = 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
  } else {
    badgeStyle = 'bg-red-500/10 text-red-400 border border-red-500/20'
  }

  return (
    <tr className="hover:bg-gray-900/10 text-white font-medium transition-colors">
      <td className="py-3.5 px-4 font-bold">{item.name}</td>
      <td className="py-3.5 px-4 text-center">{item.quantity}</td>
      <td className="py-3.5 px-4 text-right">R$ {item.avg_price.toFixed(2)}</td>
      <td className="py-3.5 px-4 text-right">R$ {item.cost.toFixed(2)}</td>
      <td
        className={`py-3.5 px-4 text-right font-black ${
          item.margin >= 0 ? 'text-emerald-400' : 'text-rose-400'
        }`}
      >
        R$ {item.margin.toFixed(2)}
      </td>
      <td className="py-3.5 px-4 text-center">
        <span
          className={`inline-block px-2 py-0.5 text-[8px] font-extrabold rounded-md whitespace-nowrap ${badgeStyle}`}
        >
          {item.classification.replace('_', ' ')}
        </span>
      </td>
      <td
        className="py-3.5 px-4 text-[10px] text-gray-400 italic font-normal max-w-[200px] truncate"
        title={item.recommendation}
      >
        {item.recommendation}
      </td>
    </tr>
  )
}

function HeatmapGrid({ heatmap }: { heatmap: NonNullable<OrderInsights['heatmap']> }) {
  const days = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb']
  const hours = Array.from({ length: 24 }, (_, i) => i)

  const maxSales = Math.max(...heatmap.map((h) => h.total_sales), 1)

  const getCellData = (dayIdx: number, hour: number) => {
    return (
      heatmap.find((h) => h.day_of_week === dayIdx + 1 && h.hour === hour) || {
        total_sales: 0,
        orders_count: 0,
      }
    )
  }

  return (
    <div className="rounded-2xl border border-gray-900 bg-gray-950/10 p-5 space-y-4 backdrop-blur-md glass-card">
      <div className="flex items-center justify-between border-b border-gray-900 pb-2">
        <h3 className="text-xs font-black uppercase tracking-widest text-gray-550">
          Heatmap de Vendas (Horários de Pico)
        </h3>
        <span className="text-[10px] text-gray-500 font-bold bg-gray-900/40 px-2 py-0.5 rounded border border-gray-850">
          Hora local (timezone GMT-3)
        </span>
      </div>

      <div className="overflow-x-auto pb-2">
        <div className="min-w-[760px] space-y-1">
          <div className="grid grid-cols-[40px_repeat(24,_1fr)] gap-1 text-[9px] font-extrabold text-gray-600 text-center">
            <div />
            {hours.map((h) => (
              <div key={h}>{h}h</div>
            ))}
          </div>

          {days.map((day, dIdx) => (
            <div key={day} className="grid grid-cols-[40px_repeat(24,_1fr)] gap-1 items-center">
              <div className="text-[10px] font-black text-gray-500 uppercase">{day}</div>
              {hours.map((h) => {
                const cell = getCellData(dIdx, h)
                const ratio = cell.total_sales / maxSales

                let cellStyle = 'bg-gray-900/40 border border-gray-950/20'
                if (ratio > 0.75) {
                  cellStyle = 'bg-brand-500 text-white font-black'
                } else if (ratio > 0.5) {
                  cellStyle = 'bg-brand-600/80'
                } else if (ratio > 0.25) {
                  cellStyle = 'bg-brand-700/50'
                } else if (ratio > 0.05) {
                  cellStyle = 'bg-brand-900/30 border border-brand-900/10'
                }

                return (
                  <div
                    key={h}
                    className={`h-6 rounded-md flex items-center justify-center text-[8px] transition-all hover:scale-110 hover:border-gray-550 cursor-pointer ${cellStyle}`}
                    title={`${day} às ${h}h: R$ ${cell.total_sales.toFixed(2)} (${cell.orders_count} comandas)`}
                  >
                    {cell.orders_count > 0 ? cell.orders_count : ''}
                  </div>
                )
              })}
            </div>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-2 justify-end text-[9px] font-extrabold text-gray-555">
        <span>Poucas Vendas</span>
        <div className="h-3.5 w-3.5 rounded bg-gray-900/40 border border-gray-950/20" />
        <div className="h-3.5 w-3.5 rounded bg-brand-900/30 border border-brand-900/10" />
        <div className="h-3.5 w-3.5 rounded bg-brand-700/50" />
        <div className="h-3.5 w-3.5 rounded bg-brand-600/80" />
        <div className="h-3.5 w-3.5 rounded bg-brand-500" />
        <span>Pico Crítico</span>
      </div>
    </div>
  )
}

function TablePerformanceGrid({ tables }: { tables: TablePerformance[] | null }) {
  if (!tables || tables.length === 0) return null

  const maxRevenue = Math.max(...tables.map((t) => t.total_revenue), 1)

  return (
    <div className="rounded-2xl border border-gray-900 bg-gray-950/10 p-5 space-y-4 backdrop-blur-md glass-card">
      <div className="flex items-center justify-between border-b border-gray-900 pb-2">
        <h3 className="text-xs font-black uppercase tracking-widest text-gray-550">
          Consumo por Mesa (Mapa do Salão)
        </h3>
        <span className="text-[10px] text-gray-500 font-bold bg-gray-900/40 px-2 py-0.5 rounded border border-gray-850">
          Faturamento Real Consolidado
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-3 pt-2">
        {tables.map((t) => {
          const ratio = t.total_revenue / maxRevenue
          let colorStyle = 'bg-gray-900/40 border border-gray-850 text-gray-400'
          if (ratio > 0.75) {
            colorStyle = 'bg-emerald-500/10 border border-emerald-500/35 text-emerald-300'
          } else if (ratio > 0.4) {
            colorStyle = 'bg-brand-500/10 border border-brand-500/30 text-brand-300'
          } else if (ratio > 0.1) {
            colorStyle = 'bg-brand-900/10 border border-brand-900/20 text-brand-400'
          }

          return (
            <div
              key={t.table_number}
              className={`rounded-xl p-4 text-center flex flex-col justify-between transition-all hover:scale-105 hover:shadow-lg cursor-pointer ${colorStyle}`}
              title={`Mesa ${t.table_number}: Total R$ ${t.total_revenue.toFixed(2)} (${t.orders_count} comandas)`}
            >
              <div className="text-[9px] uppercase font-extrabold opacity-70">Mesa</div>
              <div className="text-xl font-black py-1">{t.table_number}</div>
              <div className="text-[9px] font-bold">R$ {t.total_revenue.toFixed(0)}</div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
interface GeneralTabViewProps {
  stats: DashboardStats | null
  trendChartData: { time: string; total: number; projected?: number }[]
  categoryChartData: { name: string; valor: number }[]
  chartColors: string[]
  orderInsights: OrderInsights | null
  tablePerf: TablePerformance[] | null
}

function GeneralTabView({
  stats,
  trendChartData,
  categoryChartData,
  chartColors,
  orderInsights,
  tablePerf,
}: GeneralTabViewProps) {
  return (
    <>
      {/* KPI Cards Grid */}
      <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
        {/* Card 1: Faturamento */}
        <div className="rounded-2xl border border-gray-900/60 bg-gray-950/15 p-5 space-y-2 backdrop-blur-md glass-card">
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase font-extrabold tracking-widest text-gray-550">
              Faturamento
            </span>
            <div className="h-7 w-7 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
              <DollarSign className="h-4 w-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-white tracking-tight">
            R$ {Number(stats?.total_sales).toFixed(2)}
          </div>
        </div>

        {/* Card 2: Ticket Médio */}
        <div className="rounded-2xl border border-gray-900/60 bg-gray-950/15 p-5 space-y-2 backdrop-blur-md glass-card">
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase font-extrabold tracking-widest text-gray-550">
              Ticket Médio
            </span>
            <div className="h-7 w-7 rounded-lg bg-brand-500/10 border border-brand-500/20 flex items-center justify-center text-brand-400">
              <TrendingUp className="h-4 w-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-white tracking-tight">
            R$ {Number(stats?.average_ticket).toFixed(2)}
          </div>
        </div>

        {/* Card 3: Comandas */}
        <div className="rounded-2xl border border-gray-900/60 bg-gray-950/15 p-5 space-y-2 backdrop-blur-md glass-card">
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase font-extrabold tracking-widest text-gray-550">
              Total Pedidos
            </span>
            <div className="h-7 w-7 rounded-lg bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
              <ShoppingBag className="h-4 w-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-white tracking-tight">{stats?.orders_count}</div>
        </div>

        {/* Card 4: Prep Time */}
        <div className="rounded-2xl border border-gray-900/60 bg-gray-950/15 p-5 space-y-2 backdrop-blur-md glass-card">
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase font-extrabold tracking-widest text-gray-550">
              Tempo Conclusão Médio
            </span>
            <div className="h-7 w-7 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
              <Clock className="h-4 w-4" />
            </div>
          </div>
          <div className="text-2xl font-black text-white tracking-tight flex items-baseline gap-1">
            {stats?.average_prep_time_minutes.toFixed(1)}
            <span className="text-xs text-gray-555 font-medium">min</span>
          </div>
        </div>
      </div>

      {/* Warnings - critical stock items */}
      {stats && stats.low_stock_items > 0 && (
        <div className="flex items-center gap-3 rounded-2xl border border-amber-900/40 bg-amber-950/10 p-4 text-xs text-amber-400 backdrop-blur-md">
          <AlertTriangle className="h-5 w-5 text-amber-400 flex-shrink-0 animate-pulse" />
          <div>
            <span className="font-extrabold uppercase tracking-wide text-[10px] px-1.5 py-0.5 rounded bg-amber-500/10 border border-amber-500/20 mr-1.5">
              Alerta Estoque
            </span>
            Existem <span className="font-black underline">{stats.low_stock_items} insumos</span>{' '}
            abaixo do nível crítico de alerta. Verifique a seção de Estoque.
          </div>
        </div>
      )}

      {/* Charts Row */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Sales Trend Chart Card */}
        <div className="rounded-2xl border border-gray-900 bg-gray-950/10 p-5 space-y-5 backdrop-blur-md glass-card">
          <h3 className="text-xs font-black uppercase tracking-widest text-gray-550">
            Evolução do Faturamento Real
          </h3>
          {trendChartData.length === 0 ? (
            <div className="flex h-64 items-center justify-center text-xs text-gray-555 italic">
              Nenhuma venda realizada neste período para gerar dados de tendências.
            </div>
          ) : (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trendChartData}>
                  <defs>
                    <linearGradient id="colorTotal" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#f97316" stopOpacity={0.2} />
                      <stop offset="95%" stopColor="#f97316" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" opacity={0.3} />
                  <XAxis dataKey="time" stroke="#6b7280" fontSize={10} tickLine={false} />
                  <YAxis stroke="#6b7280" fontSize={10} tickLine={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0c0c14',
                      borderColor: '#1f2937',
                      borderRadius: '12px',
                      color: '#fff',
                      fontSize: 11,
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="total"
                    stroke="#f97316"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorTotal)"
                    name="Faturamento Real"
                  />
                  <Line
                    type="monotone"
                    dataKey="projected"
                    stroke="#8b5cf6"
                    strokeWidth={2}
                    strokeDasharray="5 5"
                    dot={false}
                    name="Previsão Estimada"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        {/* Sales by Category Chart Card */}
        <div className="rounded-2xl border border-gray-900 bg-gray-950/10 p-5 space-y-5 backdrop-blur-md glass-card">
          <h3 className="text-xs font-black uppercase tracking-widest text-gray-555">
            Vendas por Categoria
          </h3>

          {categoryChartData.length === 0 ? (
            <div className="flex h-64 items-center justify-center text-xs text-gray-555 italic">
              Nenhuma venda realizada neste período para gerar dados de categorias.
            </div>
          ) : (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={categoryChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" opacity={0.3} />
                  <XAxis dataKey="name" stroke="#6b7280" fontSize={10} tickLine={false} />
                  <YAxis stroke="#6b7280" fontSize={10} tickLine={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0c0c14',
                      borderColor: '#1f2937',
                      borderRadius: '12px',
                      color: '#fff',
                      fontSize: 11,
                    }}
                    cursor={{ fill: 'rgba(255,255,255,0.02)' }}
                  />
                  <Bar dataKey="valor" radius={[6, 6, 0, 0]} maxBarSize={45}>
                    {categoryChartData.map((entry, index) => (
                      <Cell
                        key={`cell-${entry.name}`}
                        fill={chartColors[index % chartColors.length]}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>

      {tablePerf && tablePerf.length > 0 && <TablePerformanceGrid tables={tablePerf} />}

      {orderInsights?.heatmap && orderInsights.heatmap.length > 0 && (
        <HeatmapGrid heatmap={orderInsights.heatmap} />
      )}
    </>
  )
}

interface KitchenTabViewProps {
  kitchenStats: KitchenPerformance | null
  orderFunnel: OrderFunnel | null
  isLoading: boolean
}

function OrderFunnelVisual({ funnel }: { funnel: OrderFunnel | null }) {
  if (!funnel) return null

  const stages = [
    {
      name: '1. Fila de Espera',
      value: `${funnel.avg_queue_minutes.toFixed(1)} min`,
      desc: 'Tempo até aceitar no KDS',
      color: 'bg-amber-500/10 border-amber-500/25 text-amber-400',
    },
    {
      name: '2. Preparo Ativo',
      value: `${funnel.avg_prep_minutes.toFixed(1)} min`,
      desc: 'Tempo de cozinha ativo',
      color: 'bg-blue-500/10 border-blue-500/25 text-blue-400',
    },
    {
      name: '3. Checkout & Caixa',
      value: `${funnel.avg_checkout_minutes.toFixed(1)} min`,
      desc: 'Tempo de fechamento/pagamento',
      color: 'bg-purple-500/10 border-purple-500/25 text-purple-400',
    },
    {
      name: 'Tempo Ciclo Total',
      value: `${funnel.avg_total_cycle_minutes.toFixed(1)} min`,
      desc: 'Média de abertura ao fechamento',
      color: 'bg-emerald-500/10 border-emerald-500/25 text-emerald-400 font-black',
    },
  ]

  return (
    <div className="border-t border-gray-900 pt-5 space-y-4">
      <h4 className="text-xs font-black uppercase tracking-widest text-gray-555">
        Funil de Tempo de Ciclo de Vida da Comanda
      </h4>
      <div className="grid gap-4 grid-cols-2 md:grid-cols-4">
        {stages.map((stage) => (
          <div
            key={stage.name}
            className={`border rounded-xl p-4.5 text-center flex flex-col justify-between backdrop-blur-md ${stage.color}`}
          >
            <span className="text-[9px] uppercase font-extrabold tracking-wider block opacity-80">
              {stage.name}
            </span>
            <div className="text-2xl font-black py-1.5">{stage.value}</div>
            <span className="text-[9px] text-gray-400 font-bold block">{stage.desc}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function KitchenTabView({ kitchenStats, orderFunnel, isLoading }: KitchenTabViewProps) {
  if (!kitchenStats) {
    if (!isLoading) {
      return (
        <div className="rounded-2xl border border-gray-900 bg-gray-950/10 p-5 text-center">
          <p className="text-xs text-gray-600 italic">
            Sem dados de cozinha para o período selecionado.
          </p>
        </div>
      )
    }
    return null
  }

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-gray-900 bg-gray-950/10 p-5 backdrop-blur-md glass-card space-y-5">
        <h3 className="text-xs font-black uppercase tracking-widest text-gray-555">
          Produtividade Geral da Cozinha
        </h3>

        {/* KPI Grid - Responsive columns */}
        <div className="grid gap-4 grid-cols-2 md:grid-cols-3 lg:grid-cols-6 text-center text-xs">
          <div className="border border-gray-900 bg-gray-950/20 rounded-xl p-4 space-y-1.5">
            <span className="text-[10px] text-gray-550 uppercase font-extrabold tracking-wider block">
              Pratos Preparados
            </span>
            <div className="text-xl font-black text-white">{kitchenStats.items_prepared}</div>
          </div>

          <div className="border border-gray-900 bg-gray-950/20 rounded-xl p-4 space-y-1.5">
            <span className="text-[10px] text-gray-555 uppercase font-extrabold tracking-wider block">
              Taxa de Conclusão
            </span>
            <div className="text-xl font-black text-emerald-400 flex items-center justify-center gap-1.5">
              <CheckCircle className="h-4 w-4 text-emerald-500" />
              <span>{(kitchenStats.completion_rate * 100).toFixed(0)}%</span>
            </div>
          </div>

          <div className="border border-gray-900 bg-gray-950/20 rounded-xl p-4 space-y-1.5">
            <span className="text-[10px] text-gray-555 uppercase font-extrabold tracking-wider block">
              SLA Compliance (≤15m)
            </span>
            <div className="text-xl font-black text-emerald-400 flex items-center justify-center gap-1.5">
              <span>{(kitchenStats.sla_compliance_rate * 100).toFixed(0)}%</span>
            </div>
          </div>

          <div className="border border-gray-900 bg-gray-950/20 rounded-xl p-4 space-y-1.5">
            <span className="text-[10px] text-gray-555 uppercase font-extrabold tracking-wider block">
              Tempo Médio Fila
            </span>
            <div className="text-xl font-black text-amber-400">
              {kitchenStats.average_queue_time_minutes.toFixed(1)}{' '}
              <span className="text-xs font-medium text-gray-500">min</span>
            </div>
          </div>

          <div className="border border-gray-900 bg-gray-950/20 rounded-xl p-4 space-y-1.5">
            <span className="text-[10px] text-gray-555 uppercase font-extrabold tracking-wider block">
              Tempo Médio Preparo
            </span>
            <div className="text-xl font-black text-blue-400">
              {kitchenStats.average_prep_time_minutes.toFixed(1)}{' '}
              <span className="text-xs font-medium text-gray-500">min</span>
            </div>
          </div>

          <div className="border border-gray-900 bg-gray-950/20 rounded-xl p-4 space-y-1.5">
            <span className="text-[10px] text-gray-555 uppercase font-extrabold tracking-wider block">
              Consistência (Desvio Padrão)
            </span>
            <div className="text-xl font-black text-purple-400">
              ±{kitchenStats.std_dev_prep_time_minutes.toFixed(1)}{' '}
              <span className="text-xs font-medium text-gray-500">min</span>
            </div>
          </div>
        </div>

        {/* Cancellation Waste KPI */}
        {kitchenStats.waste_cancelled_value > 0 && (
          <div className="flex items-center gap-3 rounded-xl border border-rose-900/40 bg-rose-950/10 p-4 text-xs text-rose-400">
            <AlertTriangle className="h-5 w-5 text-rose-400 flex-shrink-0 animate-pulse" />
            <div>
              <span className="font-extrabold uppercase tracking-wide text-[9px] px-1.5 py-0.5 rounded bg-rose-500/10 border border-rose-500/20 mr-1.5">
                Perda Operacional (Desperdício)
              </span>
              Pratos cancelados após envio à cozinha geraram um impacto financeiro estimado de{' '}
              <span className="font-black underline">
                R$ {kitchenStats.waste_cancelled_value.toFixed(2)}
              </span>{' '}
              ({kitchenStats.waste_cancelled_count} itens cancelados).
            </div>
          </div>
        )}

        {/* Station Performance Section */}
        {kitchenStats.by_station && Object.entries(kitchenStats.by_station).length > 0 && (
          <div className="border-t border-gray-900 pt-5 space-y-4">
            <h4 className="text-xs font-black uppercase tracking-widest text-gray-555">
              Desempenho por Estação de Cozinha
            </h4>
            <div className="grid gap-4 md:grid-cols-2">
              {Object.entries(kitchenStats.by_station).map(([station, perf]) => (
                <div
                  key={station}
                  className="border border-gray-900 bg-gray-950/20 rounded-xl p-5 space-y-3"
                >
                  <div className="flex items-center justify-between border-b border-gray-900 pb-2">
                    <span className="text-xs font-extrabold uppercase text-white tracking-wide">
                      {station}
                    </span>
                    <span className="text-[10px] text-gray-550 font-bold bg-gray-900/40 px-2 py-0.5 rounded border border-gray-850">
                      {perf.items_prepared} itens
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-4 text-center">
                    <div className="space-y-1">
                      <span className="text-[9px] text-gray-555 uppercase tracking-wider block">
                        Tempo de Fila
                      </span>
                      <div className="text-sm font-black text-amber-400">
                        {perf.average_queue_time_minutes.toFixed(1)} min
                      </div>
                    </div>
                    <div className="space-y-1">
                      <span className="text-[9px] text-gray-555 uppercase tracking-wider block">
                        Tempo de Preparo
                      </span>
                      <div className="text-sm font-black text-blue-400">
                        {perf.average_prep_time_minutes.toFixed(1)} min
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <OrderFunnelVisual funnel={orderFunnel} />
      </div>

      {/* Bottlenecks Section */}
      <div className="border-t border-gray-900 pt-5 space-y-4">
        <h4 className="text-xs font-black uppercase tracking-widest text-gray-555">
          Gargalos de Cozinha (Top 5 Mais Lentos)
        </h4>
        {!kitchenStats.bottlenecks || kitchenStats.bottlenecks.length === 0 ? (
          <p className="text-xs text-gray-650 italic py-8 text-center">
            Nenhum gargalo de tempo identificado no período.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-gray-900 text-gray-555 uppercase tracking-wider text-[9px] font-extrabold">
                  <th className="py-2.5 px-2">Prato</th>
                  <th className="py-2.5 px-2 text-center">Prep. Médio</th>
                  <th className="py-2.5 px-2 text-center">Quant. Preparada</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-900/35">
                {kitchenStats.bottlenecks.map((item) => (
                  <tr key={item.name} className="hover:bg-gray-900/5 text-white font-medium">
                    <td className="py-3 px-2 font-bold">{item.name}</td>
                    <td className="py-3 px-2 text-center text-rose-455 font-extrabold">
                      {item.average_prep_time_minutes.toFixed(1)} min
                    </td>
                    <td className="py-3 px-2 text-center">{item.items_prepared}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Throughput chart */}
      <div className="rounded-2xl border border-gray-900 bg-gray-950/10 p-5 space-y-4 backdrop-blur-md glass-card">
        <h4 className="text-xs font-black uppercase tracking-widest text-gray-555">
          Volume de Produção (Throughput)
        </h4>
        {!kitchenStats.throughput_trends || kitchenStats.throughput_trends.length === 0 ? (
          <div className="flex h-52 items-center justify-center text-xs text-gray-555 italic">
            Nenhuma produção concluída neste período para gerar tendências.
          </div>
        ) : (
          <div className="h-52">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={kitchenStats.throughput_trends}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" opacity={0.3} />
                <XAxis dataKey="time" stroke="#6b7280" fontSize={9} tickLine={false} />
                <YAxis stroke="#6b7280" fontSize={9} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0c0c14',
                    borderColor: '#1f2937',
                    borderRadius: '12px',
                    color: '#fff',
                    fontSize: 10,
                  }}
                  cursor={{ fill: 'rgba(255,255,255,0.01)' }}
                />
                <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} maxBarSize={30} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
      <div className="rounded-2xl border border-gray-900 bg-gray-950/10 p-5 space-y-4 backdrop-blur-md glass-card">
        <h4 className="text-xs font-black uppercase tracking-widest text-gray-555">
          Distribuição de Tempo: Fila vs. Preparo Ativo
        </h4>
        {!kitchenStats.queue_vs_prep_trends || kitchenStats.queue_vs_prep_trends.length === 0 ? (
          <div className="flex h-48 items-center justify-center text-xs text-gray-555 italic">
            Sem dados de fila vs. preparo disponíveis no período.
          </div>
        ) : (
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={kitchenStats.queue_vs_prep_trends}>
                <defs>
                  <linearGradient id="colorQueue" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorPrep" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" opacity={0.3} />
                <XAxis dataKey="time" stroke="#6b7280" fontSize={9} tickLine={false} />
                <YAxis stroke="#6b7280" fontSize={9} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0c0c14',
                    borderColor: '#1f2937',
                    borderRadius: '12px',
                    color: '#fff',
                    fontSize: 10,
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="queue_minutes"
                  stackId="1"
                  stroke="#f59e0b"
                  fillOpacity={1}
                  fill="url(#colorQueue)"
                  name="Tempo de Fila (Espera)"
                />
                <Area
                  type="monotone"
                  dataKey="prep_minutes"
                  stackId="1"
                  stroke="#3b82f6"
                  fillOpacity={1}
                  fill="url(#colorPrep)"
                  name="Tempo de Preparo Ativo"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  )
}

function MarginSandbox({
  items,
  averageMargin,
}: {
  items: MenuMatrixItem[]
  averageMargin: number
}) {
  const [selectedItemId, setSelectedItemId] = useState<number | ''>('')
  const [customPrice, setCustomPrice] = useState<number>(0)
  const [customCost, setCustomCost] = useState<number>(0)

  const selectedItem = items.find((i) => i.menu_item_id === selectedItemId)

  useEffect(() => {
    if (selectedItem) {
      setCustomPrice(selectedItem.avg_price)
      setCustomCost(selectedItem.cost)
    }
  }, [selectedItem])

  const newMargin = customPrice - customCost
  const newMarginPct = customPrice > 0 ? (newMargin / customPrice) * 100 : 0
  const originalMargin = selectedItem ? selectedItem.margin : 0
  const originalMarginPct =
    selectedItem && selectedItem.avg_price > 0
      ? (selectedItem.margin / selectedItem.avg_price) * 100
      : 0

  const simulatedAverageMargin = (() => {
    if (!selectedItem || items.length === 0) return averageMargin
    const otherItemsMarginSum = items
      .filter((i) => i.menu_item_id !== selectedItemId)
      .reduce((sum, i) => sum + i.margin, 0)
    return (otherItemsMarginSum + newMargin) / items.length
  })()

  return (
    <div className="rounded-2xl border border-gray-900 bg-gray-950/10 p-5 backdrop-blur-md glass-card space-y-4">
      <div className="flex items-center gap-2 border-b border-gray-900 pb-3">
        <Sliders className="h-4 w-4 text-brand-400" />
        <h3 className="text-xs font-black uppercase tracking-widest text-gray-555">
          Sandbox: Simulador Interativo de Margem de Lucro
        </h3>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        <div className="space-y-2">
          <label
            htmlFor="sandbox-select"
            className="text-[10px] text-gray-450 uppercase font-extrabold tracking-wider block"
          >
            Selecionar Prato
          </label>
          <select
            id="sandbox-select"
            value={selectedItemId}
            onChange={(e) => setSelectedItemId(e.target.value ? Number(e.target.value) : '')}
            className="w-full rounded-xl bg-gray-900 border border-gray-805 p-3 text-xs text-white outline-none focus:border-brand-500 transition-colors"
          >
            <option value="">-- Escolha um prato --</option>
            {items.map((item) => (
              <option key={item.menu_item_id} value={item.menu_item_id}>
                {item.name}
              </option>
            ))}
          </select>
          <p className="text-[10px] text-gray-500 italic">
            Selecione um item do cardápio para simular novos preços de venda ou de custo.
          </p>
        </div>

        {selectedItem ? (
          <div className="space-y-4">
            <div className="space-y-1.5">
              <div className="flex justify-between text-[10px] font-extrabold uppercase tracking-wide">
                <span className="text-gray-450">Preço de Venda</span>
                <span className="text-white">R$ {customPrice.toFixed(2)}</span>
              </div>
              <input
                type="range"
                min={1}
                max={Math.max(selectedItem.avg_price * 2.5, 100)}
                step={0.5}
                value={customPrice}
                onChange={(e) => setCustomPrice(Number(e.target.value))}
                className="w-full h-1 bg-gray-800 rounded-lg appearance-none cursor-pointer accent-brand-500"
              />
            </div>

            <div className="space-y-1.5">
              <div className="flex justify-between text-[10px] font-extrabold uppercase tracking-wide">
                <span className="text-gray-450">Preço de Custo (Insumos)</span>
                <span className="text-white">R$ {customCost.toFixed(2)}</span>
              </div>
              <input
                type="range"
                min={0}
                max={Math.max(selectedItem.cost * 2.5, 100)}
                step={0.5}
                value={customCost}
                onChange={(e) => setCustomCost(Number(e.target.value))}
                className="w-full h-1 bg-gray-800 rounded-lg appearance-none cursor-pointer accent-brand-500"
              />
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center border border-dashed border-gray-850 rounded-xl p-6 text-center text-xs text-gray-650 italic">
            Nenhum prato selecionado para simulação.
          </div>
        )}

        {selectedItem ? (
          <div className="border border-gray-900 bg-gray-950/20 rounded-xl p-4.5 space-y-3">
            <h4 className="text-[10px] font-extrabold uppercase tracking-wider text-gray-555 border-b border-gray-900 pb-1.5">
              Impacto Projetado
            </h4>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-gray-500 font-bold">Margem Unitária:</span>
                <div className="text-right">
                  <div className="text-white font-extrabold">
                    R$ {newMargin.toFixed(2)} ({newMarginPct.toFixed(0)}%)
                  </div>
                  <div className="text-[10px] text-gray-600 line-through">
                    R$ {originalMargin.toFixed(2)} ({originalMarginPct.toFixed(0)}%)
                  </div>
                </div>
              </div>
              <div className="flex justify-between border-t border-gray-900/50 pt-2">
                <span className="text-gray-500 font-bold">Margem Média do Cardápio:</span>
                <div className="text-right">
                  <div
                    className={`font-black ${simulatedAverageMargin >= averageMargin ? 'text-emerald-400' : 'text-rose-400'}`}
                  >
                    R$ {simulatedAverageMargin.toFixed(2)}
                  </div>
                  <div className="text-[10px] text-gray-600">
                    Original: R$ {averageMargin.toFixed(2)}
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center border border-dashed border-gray-850 rounded-xl p-6 text-center text-xs text-gray-650 italic">
            Aguardando seleção de prato...
          </div>
        )}
      </div>
    </div>
  )
}

interface MenuMatrixTabViewProps {
  menuMatrix: MenuMatrixReport | null
  eliteItems: MenuMatrixItem[]
  oportunidadeItems: MenuMatrixItem[]
  volumeItems: MenuMatrixItem[]
  baixoDesempenhoItems: MenuMatrixItem[]
  combos: ComboRecommendation[] | null
  cannibalization: CannibalizationWarning[] | null
}

function MenuMatrixTabView({
  menuMatrix,
  eliteItems,
  oportunidadeItems,
  volumeItems,
  baixoDesempenhoItems,
  combos,
  cannibalization,
}: MenuMatrixTabViewProps) {
  return (
    <div className="space-y-6">
      {/* Matrix Layout Grid */}
      <div className="rounded-2xl border border-gray-900 bg-gray-950/10 p-5 backdrop-blur-md glass-card space-y-4">
        <div className="flex items-center justify-between border-b border-gray-900 pb-3">
          <div>
            <h3 className="text-xs font-black uppercase tracking-widest text-gray-550">
              Matriz de Engenharia de Cardápio
            </h3>
            <p className="text-[10px] text-gray-500 mt-0.5">
              Classificação baseada em Popularidade (Volume de vendas) vs Rentabilidade (Margem
              bruta)
            </p>
          </div>
          <div className="flex items-center gap-1 text-[10px] text-gray-550 font-bold bg-gray-900/30 px-3 py-1.5 rounded-xl border border-gray-900">
            <Info className="h-3.5 w-3.5 text-brand-400" />
            <span>Calculado a partir de compras reais</span>
          </div>
        </div>

        {/* 2x2 Matrix UI */}
        <div className="grid gap-4 md:grid-cols-2">
          {/* ELITE - High Pop, High Profit */}
          <div className="border border-emerald-500/20 bg-emerald-950/5 rounded-2xl p-5 space-y-3">
            <div className="flex items-center justify-between border-b border-emerald-500/10 pb-2">
              <span className="text-xs font-extrabold uppercase text-emerald-400 tracking-wide flex items-center gap-1.5">
                💎 ELITE
              </span>
              <span className="text-[9px] bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 font-bold px-2 py-0.5 rounded">
                Alta Venda / Alta Margem
              </span>
            </div>
            {eliteItems.length === 0 ? (
              <p className="text-[11px] text-gray-555 italic">Sem itens neste quadrante</p>
            ) : (
              <div className="flex flex-wrap gap-1.5">
                {eliteItems.map((item) => (
                  <span
                    key={item.menu_item_id}
                    className="text-[10px] font-bold bg-gray-900 border border-gray-800 text-white px-2 py-1 rounded-lg"
                  >
                    {item.name} ({item.quantity})
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* OPORTUNIDADE - Low Pop, High Profit */}
          <div className="border border-brand-500/20 bg-brand-950/5 rounded-2xl p-5 space-y-3">
            <div className="flex items-center justify-between border-b border-brand-500/10 pb-2">
              <span className="text-xs font-extrabold uppercase text-brand-400 tracking-wide flex items-center gap-1.5">
                🚀 OPORTUNIDADE
              </span>
              <span className="text-[9px] bg-brand-500/10 border border-brand-500/20 text-brand-300 font-bold px-2 py-0.5 rounded">
                Baixa Venda / Alta Margem
              </span>
            </div>
            {oportunidadeItems.length === 0 ? (
              <p className="text-[11px] text-gray-555 italic">Sem itens neste quadrante</p>
            ) : (
              <div className="flex flex-wrap gap-1.5">
                {oportunidadeItems.map((item) => (
                  <span
                    key={item.menu_item_id}
                    className="text-[10px] font-bold bg-gray-900 border border-gray-800 text-white px-2 py-1 rounded-lg"
                  >
                    {item.name} ({item.quantity})
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* ALTO VOLUME - High Pop, Low Profit */}
          <div className="border border-amber-500/20 bg-amber-950/5 rounded-2xl p-5 space-y-3">
            <div className="flex items-center justify-between border-b border-amber-500/10 pb-2">
              <span className="text-xs font-extrabold uppercase text-amber-400 tracking-wide flex items-center gap-1.5">
                📈 ALTO VOLUME
              </span>
              <span className="text-[9px] bg-amber-500/10 border border-amber-500/20 text-amber-300 font-bold px-2 py-0.5 rounded">
                Alta Venda / Baixa Margem
              </span>
            </div>
            {volumeItems.length === 0 ? (
              <p className="text-[11px] text-gray-555 italic">Sem itens neste quadrante</p>
            ) : (
              <div className="flex flex-wrap gap-1.5">
                {volumeItems.map((item) => (
                  <span
                    key={item.menu_item_id}
                    className="text-[10px] font-bold bg-gray-900 border border-gray-800 text-white px-2 py-1 rounded-lg"
                  >
                    {item.name} ({item.quantity})
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* BAIXO DESEMPENHO - Low Pop, Low Profit */}
          <div className="border border-red-500/20 bg-red-950/5 rounded-2xl p-5 space-y-3">
            <div className="flex items-center justify-between border-b border-red-500/10 pb-2">
              <span className="text-xs font-extrabold uppercase text-red-400 tracking-wide flex items-center gap-1.5">
                ⚠️ BAIXO DESEMPENHO
              </span>
              <span className="text-[9px] bg-red-500/10 border border-red-500/20 text-red-300 font-bold px-2 py-0.5 rounded">
                Baixa Venda / Baixa Margem
              </span>
            </div>
            {baixoDesempenhoItems.length === 0 ? (
              <p className="text-[11px] text-gray-555 italic">Sem itens neste quadrante</p>
            ) : (
              <div className="flex flex-wrap gap-1.5">
                {baixoDesempenhoItems.map((item) => (
                  <span
                    key={item.menu_item_id}
                    className="text-[10px] font-bold bg-gray-900 border border-gray-800 text-white px-2 py-1 rounded-lg"
                  >
                    {item.name} ({item.quantity})
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Items List Table */}
      <div className="rounded-2xl border border-gray-900 bg-gray-950/10 p-5 backdrop-blur-md glass-card space-y-4">
        <h3 className="text-xs font-black uppercase tracking-widest text-gray-555">
          Desempenho Detalhado de Pratos
        </h3>
        {menuMatrix?.items && menuMatrix.items.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-gray-900 text-gray-550 uppercase tracking-wider text-[9px] font-extrabold">
                  <th className="py-3 px-4">Nome do Item</th>
                  <th className="py-3 px-4 text-center">Quant. Vendida</th>
                  <th className="py-3 px-4 text-right">Preço Médio</th>
                  <th className="py-3 px-4 text-right">Custo Insumos</th>
                  <th className="py-3 px-4 text-right">Margem Unitária</th>
                  <th className="py-3 px-4 text-center">Classificação</th>
                  <th className="py-3 px-4">Recomendação Gerencial</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-900/40">
                {menuMatrix.items.map((item) => (
                  <MenuMatrixTableRow key={item.menu_item_id} item={item} />
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-xs text-gray-555 italic text-center py-6">
            Nenhum prato vendido no período selecionado.
          </p>
        )}
      </div>

      {/* Cannibalization Warnings */}
      {cannibalization && cannibalization.length > 0 && (
        <div className="rounded-2xl border border-rose-500/20 bg-rose-955/5 p-5 backdrop-blur-md glass-card space-y-4">
          <div className="flex items-center gap-2 border-b border-rose-500/10 pb-3">
            <AlertTriangle className="h-4 w-4 text-rose-400" />
            <h3 className="text-xs font-black uppercase tracking-widest text-rose-300">
              Alertas de Canibalização de Pratos
            </h3>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            {cannibalization.map((warning) => (
              <div
                key={`${warning.cannibalized_item_id}-${warning.growing_item_id}`}
                className="border border-gray-900 bg-gray-950/20 rounded-xl p-4 space-y-2.5 text-xs text-white"
              >
                <div className="flex justify-between items-center">
                  <span className="font-bold text-[10px] text-gray-400 uppercase tracking-wider">
                    Categoria: {warning.category}
                  </span>
                  <span
                    className={`px-1.5 py-0.5 rounded text-[8px] font-extrabold border ${
                      warning.confidence === 'HIGH'
                        ? 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                        : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                    }`}
                  >
                    Confiança {warning.confidence}
                  </span>
                </div>
                <p className="text-[11px] text-gray-350">
                  O prato{' '}
                  <span className="font-extrabold text-emerald-400">
                    {warning.growing_item_name}
                  </span>{' '}
                  subiu{' '}
                  <span className="font-extrabold text-emerald-400">
                    +{warning.growing_pct.toFixed(0)}%
                  </span>{' '}
                  (venda de +{warning.growing_rise}), canibalizando o prato{' '}
                  <span className="font-extrabold text-rose-400">
                    {warning.cannibalized_item_name}
                  </span>{' '}
                  que caiu{' '}
                  <span className="font-extrabold text-rose-400">
                    -{warning.cannibalized_pct.toFixed(0)}%
                  </span>{' '}
                  (venda de -{warning.cannibalized_drop}).
                </p>
                <p className="text-[10px] text-gray-500 italic">
                  Sugestão: Avalie a margem de {warning.growing_item_name}. Se for menor, reajuste
                  os preços para restaurar a margem geral.
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Combo Recommendations */}
      {combos && combos.length > 0 && (
        <div className="rounded-2xl border border-gray-900 bg-gray-950/10 p-5 backdrop-blur-md glass-card space-y-4">
          <div className="flex items-center gap-2 border-b border-gray-900 pb-3">
            <TrendingUp className="h-4 w-4 text-brand-400" />
            <h3 className="text-xs font-black uppercase tracking-widest text-gray-555">
              Recomendações Inteligentes de Combos (Cross-Selling)
            </h3>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            {combos.map((combo) => (
              <div
                key={`${combo.item_a}-${combo.item_b}`}
                className="border border-gray-900 bg-gray-950/20 rounded-xl p-4 space-y-3 text-xs text-white"
              >
                <div className="flex justify-between items-center border-b border-gray-900 pb-1.5">
                  <span className="font-bold text-brand-400 text-[10px] uppercase tracking-wider">
                    Sugerir Combo
                  </span>
                  <span className="text-[9px] text-gray-400 font-extrabold">
                    {combo.co_occurrences} ocorrências
                  </span>
                </div>
                <div className="flex items-center gap-2 justify-center py-2">
                  <span className="bg-gray-900 border border-gray-800 px-2.5 py-1 rounded-lg text-center font-bold min-w-[80px]">
                    {combo.item_a}
                  </span>
                  <span className="text-gray-500 font-extrabold text-sm">+</span>
                  <span className="bg-gray-900 border border-gray-800 px-2.5 py-1 rounded-lg text-center font-bold min-w-[80px]">
                    {combo.item_b}
                  </span>
                </div>
                <div className="space-y-1 text-[10px] text-gray-400 pt-1 border-t border-gray-900/50">
                  <div className="flex justify-between">
                    <span>Confiança (A → B):</span>
                    <span className="font-bold text-white">
                      {(combo.confidence_a_to_b * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Confiança (B → A):</span>
                    <span className="font-bold text-white">
                      {(combo.confidence_b_to_a * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Interactive Margin Sandbox Simulator */}
      {menuMatrix?.items && (
        <MarginSandbox items={menuMatrix.items} averageMargin={menuMatrix.average_margin} />
      )}
    </div>
  )
}

import { keepPreviousData, useQuery } from '@tanstack/react-query'

export default function AnalyticsDashboard() {
  const [period, setPeriod] = useState<'day' | 'week' | 'month' | 'custom'>('day')
  const [startDate, setStartDate] = useState<string>('')
  const [endDate, setEndDate] = useState<string>('')
  const [activeTab, setActiveTab] = useState<'general' | 'kitchen' | 'menu-matrix'>('general')

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['analytics', period, startDate, endDate],
    queryFn: async () => {
      const params: Record<string, string> = { period }
      if (period === 'custom' && startDate) {
        params.start_date = new Date(startDate).toISOString()
        if (endDate) {
          params.end_date = new Date(endDate).toISOString()
        }
      }

      const [
        statsRes,
        salesRes,
        kitchenRes,
        matrixRes,
        ordersRes,
        forecastRes,
        funnelRes,
        tablesRes,
        combosRes,
        cannibalRes,
      ] = await Promise.all([
        httpClient.get<DashboardStats>('/v1/analytics/dashboard', { params }),
        httpClient.get<SalesReport>('/v1/analytics/sales', { params }),
        httpClient.get<KitchenPerformance>('/v1/analytics/kitchen', { params }),
        httpClient.get<MenuMatrixReport>('/v1/analytics/menu-matrix', { params }),
        httpClient.get<OrderInsights>('/v1/analytics/orders', { params }),
        httpClient.get<DemandForecast[]>('/v1/analytics/demand-forecast'),
        httpClient.get<OrderFunnel>('/v1/analytics/order-funnel', { params }),
        httpClient.get<TablePerformance[]>('/v1/analytics/table-performance', {
          params,
        }),
        httpClient.get<ComboRecommendation[]>('/v1/analytics/combo-recommendations'),
        httpClient.get<CannibalizationWarning[]>('/v1/analytics/cannibalization-warnings'),
      ])

      return {
        stats: statsRes.data,
        salesReport: salesRes.data,
        kitchenStats: kitchenRes.data,
        menuMatrix: matrixRes.data,
        orderInsights: ordersRes.data,
        demandForecast: forecastRes.data,
        orderFunnel: funnelRes.data,
        tablePerf: tablesRes.data,
        combos: combosRes.data,
        cannibalization: cannibalRes.data,
      }
    },
    staleTime: 1000 * 60 * 5, // 5 minutes
    placeholderData: keepPreviousData,
  })

  const {
    stats = null,
    salesReport = null,
    kitchenStats = null,
    menuMatrix = null,
    orderInsights = null,
    demandForecast = null,
    orderFunnel = null,
    tablePerf = null,
    combos = null,
    cannibalization = null,
  } = data || {}

  // Transform category data for Recharts Bar Chart
  const categoryChartData = useMemo(
    () =>
      Object.entries(salesReport?.by_category || {}).map(([category, val]) => ({
        name: category,
        valor: Number(val),
      })),
    [salesReport?.by_category],
  )

  // Real trend data from sales report, merged with demand forecast projections
  const trendChartData = useMemo(() => {
    const trends = salesReport?.trends || []
    if (!demandForecast || demandForecast.length === 0) return trends

    const trendsMap = new Map(trends.map((t) => [t.time, t.total]))
    const forecastMap = new Map(demandForecast.map((f) => [f.time, f.total]))

    const allTimes = Array.from(
      new Set([...trends.map((t) => t.time), ...demandForecast.map((f) => f.time)]),
    ).sort()

    return allTimes.map((time) => ({
      time,
      total: trendsMap.get(time) ?? 0,
      projected: forecastMap.get(time),
    }))
  }, [salesReport?.trends, demandForecast])

  // Premium harmonized category chart colors
  const chartColors = ['#f97316', '#8b5cf6', '#06b6d4', '#10b981', '#f43f5e']

  // Categorized matrix items
  const eliteItems = menuMatrix?.items.filter((i) => i.classification === 'ELITE') || []
  const oportunidadeItems =
    menuMatrix?.items.filter((i) => i.classification === 'OPORTUNIDADE') || []
  const volumeItems = menuMatrix?.items.filter((i) => i.classification === 'ALTO_VOLUME') || []
  const baixoDesempenhoItems =
    menuMatrix?.items.filter((i) => i.classification === 'BAIXO_DESEMPENHO') || []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-gray-900/60 pb-4">
        <div>
          <h2 className="text-lg font-black text-white tracking-wide uppercase">
            Painel Analytics Premium
          </h2>
          <p className="text-xs text-gray-555 font-medium mt-0.5">
            Engenharia de cardápio, produtividade por estação e faturamento em tempo real
          </p>
        </div>
        {/* Filters */}
        <div className="flex flex-col sm:flex-row items-end sm:items-center gap-3">
          {period === 'custom' && (
            <div className="flex items-center gap-2 animate-fade-in">
              <div className="relative group">
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="bg-gray-950/40 border border-gray-900 rounded-xl px-3 py-1.5 text-[10px] font-bold text-white focus:border-brand-500 outline-none transition-all"
                />
                <span className="absolute -top-4 left-1 text-[8px] uppercase font-black text-gray-600 group-focus-within:text-brand-500">
                  Início
                </span>
              </div>
              <span className="text-gray-700 text-xs font-black">/</span>
              <div className="relative group">
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="bg-gray-950/40 border border-gray-900 rounded-xl px-3 py-1.5 text-[10px] font-bold text-white focus:border-brand-500 outline-none transition-all"
                />
                <span className="absolute -top-4 left-1 text-[8px] uppercase font-black text-gray-600 group-focus-within:text-brand-500">
                  Fim
                </span>
              </div>
              {startDate && (
                <button
                  type="button"
                  onClick={() => {
                    setStartDate('')
                    setEndDate('')
                  }}
                  className="p-1.5 rounded-lg hover:bg-gray-900 text-gray-600 hover:text-rose-400 transition"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          )}
          <div className="flex bg-gray-950/40 border border-gray-900 rounded-xl p-1">
            {[
              { id: 'day', label: 'Hoje' },
              { id: 'week', label: 'Semana' },
              { id: 'month', label: 'Mês' },
              { id: 'custom', label: 'Personalizado', icon: Calendar },
            ].map((p) => (
              <button
                type="button"
                key={p.id}
                onClick={() => setPeriod(p.id as 'day' | 'week' | 'month' | 'custom')}
                className={`rounded-lg px-3.5 py-1.5 text-[10px] font-extrabold uppercase tracking-wider transition-all duration-300 flex items-center gap-1.5 ${
                  period === p.id
                    ? 'bg-brand-500 text-white shadow-md shadow-brand-500/10'
                    : 'text-gray-400 hover:text-gray-200'
                }`}
              >
                {p.icon && <p.icon className="h-3 w-3" />}
                {p.label}
              </button>
            ))}
          </div>
          <button
            type="button"
            onClick={() => refetch()}
            className="rounded-xl bg-gray-900/30 border border-gray-855 p-2.5 text-gray-400 hover:text-white transition-all duration-300"
            title="Atualizar Indicadores"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>
      {/* Tabs Navigation */}
      <div className="flex border-b border-gray-900">
        {[
          { id: 'general', label: 'Visão Geral', icon: Activity },
          { id: 'kitchen', label: 'Operações Cozinha', icon: Clock },
          { id: 'menu-matrix', label: 'Engenharia de Cardápio', icon: Utensils },
        ].map((tab) => {
          const Icon = tab.icon
          return (
            <button
              type="button"
              key={tab.id}
              onClick={() => setActiveTab(tab.id as 'general' | 'kitchen' | 'menu-matrix')}
              className={`flex items-center gap-2 px-5 py-3 text-xs font-bold transition-all duration-300 border-b-2 ${
                activeTab === tab.id
                  ? 'border-brand-500 text-brand-400 font-extrabold bg-brand-500/5'
                  : 'border-transparent text-gray-450 hover:text-gray-255 hover:bg-gray-900/10'
              }`}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
            </button>
          )
        })}
      </div>
      {isFetching && !stats ? (
        <div className="flex py-24 justify-center items-center gap-2.5">
          <Loader2 className="h-6 w-6 animate-spin text-brand-400" />
          <span className="text-xs text-gray-455 font-medium">
            Calculando estatísticas analíticas...
          </span>
        </div>
      ) : error ? (
        <div className="rounded-2xl border border-red-955 bg-red-950/20 p-6 text-center text-red-400 font-bold text-xs">
          Erro ao carregar dados analíticos. Tente novamente.
        </div>
      ) : (
        <div className="space-y-6 animate-fade-in">
          {activeTab === 'general' && (
            <GeneralTabView
              stats={stats}
              trendChartData={trendChartData}
              categoryChartData={categoryChartData}
              chartColors={chartColors}
              orderInsights={orderInsights}
              tablePerf={tablePerf}
            />
          )}
          {activeTab === 'kitchen' && (
            <KitchenTabView
              kitchenStats={kitchenStats}
              orderFunnel={orderFunnel}
              isLoading={isLoading}
            />
          )}
          {activeTab === 'menu-matrix' && (
            <MenuMatrixTabView
              menuMatrix={menuMatrix}
              eliteItems={eliteItems}
              oportunidadeItems={oportunidadeItems}
              volumeItems={volumeItems}
              baixoDesempenhoItems={baixoDesempenhoItems}
              combos={combos}
              cannibalization={cannibalization}
            />
          )}
        </div>
      )}
    </div>
  )
}

// Simple loader helper inside file scope
function Loader2({ className }: { className?: string }) {
  return (
    <div
      className={`h-5 w-5 animate-spin rounded-full border-2 border-brand-500 border-t-transparent ${className}`}
    />
  )
}
