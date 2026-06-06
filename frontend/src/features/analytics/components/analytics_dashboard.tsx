import {
  AlertTriangle,
  CheckCircle,
  Clock,
  DollarSign,
  RefreshCw,
  ShoppingBag,
  TrendingUp,
} from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
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
}

interface KitchenPerformance {
  period: string
  average_prep_time_minutes: number
  items_prepared: number
  completion_rate: number
}

export default function AnalyticsDashboard() {
  const [period, setPeriod] = useState<'day' | 'week' | 'month'>('day')
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [salesReport, setSalesReport] = useState<SalesReport | null>(null)
  const [kitchenStats, setKitchenStats] = useState<KitchenPerformance | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchAnalytics = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const [statsRes, salesRes, kitchenRes] = await Promise.all([
        httpClient.get<DashboardStats>('/v1/analytics/dashboard', {
          params: { period: period },
        }),
        httpClient.get<SalesReport>('/v1/analytics/sales', {
          params: { period: period },
        }),
        httpClient.get<KitchenPerformance>('/v1/analytics/kitchen', {
          params: { period: period },
        }),
      ])

      setStats(statsRes.data)
      setSalesReport(salesRes.data)
      setKitchenStats(kitchenRes.data)
    } catch (_err) {
      setError('Erro ao carregar dados analíticos. Tente novamente.')
    } finally {
      setIsLoading(false)
    }
  }, [period])

  useEffect(() => {
    fetchAnalytics()
  }, [fetchAnalytics])

  // Transform category data for Recharts Bar Chart
  const categoryChartData = Object.entries(salesReport?.by_category || {}).map(
    ([category, val]) => ({
      name: category,
      valor: Number(val),
    }),
  )

  // Seed mock trend data based on period for a premium Line/Area chart visual
  const trendChartData = (() => {
    if (period === 'day') {
      return [
        { time: '11:00', total: 120 },
        { time: '12:00', total: 450 },
        { time: '13:00', total: 600 },
        { time: '14:00', total: 200 },
        { time: '18:00', total: 300 },
        { time: '19:00', total: 800 },
        { time: '20:00', total: 950 },
        { time: '21:00', total: 500 },
      ]
    }
    if (period === 'week') {
      return [
        { time: 'Seg', total: 1200 },
        { time: 'Ter', total: 1800 },
        { time: 'Qua', total: 1500 },
        { time: 'Qui', total: 2200 },
        { time: 'Sex', total: 3500 },
        { time: 'Sáb', total: 4200 },
        { time: 'Dom', total: 3805 },
      ]
    }
    return [
      { time: 'Semana 1', total: 12000 },
      { time: 'Semana 2', total: 15400 },
      { time: 'Semana 3', total: 18900 },
      { time: 'Semana 4', total: 22100 },
    ]
  })()

  // Premium harmonized category chart colors
  const chartColors = ['#f97316', '#8b5cf6', '#06b6d4', '#10b981', '#f43f5e']

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-gray-900/60 pb-4">
        <div>
          <h2 className="text-lg font-black text-white tracking-wide uppercase">
            Painel Analytics
          </h2>
          <p className="text-xs text-gray-500 font-medium mt-0.5">
            Análise de vendas, faturamento e tempos operacionais de cozinha
          </p>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-2">
          <div className="flex bg-gray-950/40 border border-gray-900 rounded-xl p-1">
            {[
              { id: 'day', label: 'Hoje' },
              { id: 'week', label: 'Semana' },
              { id: 'month', label: 'Mês' },
            ].map((p) => (
              <button
                type="button"
                key={p.id}
                onClick={() => setPeriod(p.id as 'day' | 'week' | 'month')}
                className={`rounded-lg px-3.5 py-1.5 text-[10px] font-extrabold uppercase tracking-wider transition-all duration-300 ${
                  period === p.id
                    ? 'bg-brand-500 text-white shadow-md shadow-brand-500/10'
                    : 'text-gray-400 hover:text-gray-200'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>

          <button
            type="button"
            onClick={fetchAnalytics}
            className="rounded-xl bg-gray-900/30 border border-gray-850 p-2.5 text-gray-400 hover:text-white transition-all duration-300"
            title="Atualizar Indicadores"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {isLoading && !stats ? (
        <div className="flex py-24 justify-center items-center gap-2.5">
          <Loader2 className="h-6 w-6 animate-spin text-brand-400" />
          <span className="text-xs text-gray-400 font-medium">
            Calculando estatísticas analíticas...
          </span>
        </div>
      ) : error ? (
        <div className="rounded-2xl border border-red-955 bg-red-950/20 p-6 text-center text-red-400 font-bold text-xs">
          {error}
        </div>
      ) : (
        <div className="space-y-6 animate-fade-in">
          {/* KPI Cards Grid */}
          <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
            {/* Card 1: Faturamento */}
            <div className="rounded-2xl border border-gray-900/60 bg-gray-950/15 p-5 space-y-2 backdrop-blur-md glass-card">
              <div className="flex items-center justify-between">
                <span className="text-[10px] uppercase font-extrabold tracking-widest text-gray-500">
                  Faturamento
                </span>
                <div className="h-7 w-7 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-455">
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
                <span className="text-[10px] uppercase font-extrabold tracking-widest text-gray-500">
                  Ticket Médio
                </span>
                <div className="h-7 w-7 rounded-lg bg-brand-500/10 border border-brand-500/20 flex items-center justify-center text-brand-455">
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
                <span className="text-[10px] uppercase font-extrabold tracking-widest text-gray-500">
                  Total Pedidos
                </span>
                <div className="h-7 w-7 rounded-lg bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-455">
                  <ShoppingBag className="h-4 w-4" />
                </div>
              </div>
              <div className="text-2xl font-black text-white tracking-tight">
                {stats?.orders_count}
              </div>
            </div>

            {/* Card 4: Prep Time */}
            <div className="rounded-2xl border border-gray-900/60 bg-gray-950/15 p-5 space-y-2 backdrop-blur-md glass-card">
              <div className="flex items-center justify-between">
                <span className="text-[10px] uppercase font-extrabold tracking-widest text-gray-500">
                  Preparo Médio
                </span>
                <div className="h-7 w-7 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-455">
                  <Clock className="h-4 w-4" />
                </div>
              </div>
              <div className="text-2xl font-black text-white tracking-tight flex items-baseline gap-1">
                {stats?.average_prep_time_minutes.toFixed(1)}
                <span className="text-xs text-gray-500 font-medium">min</span>
              </div>
            </div>
          </div>

          {/* Warnings - critical stock items */}
          {stats && stats.low_stock_items > 0 && (
            <div className="flex items-center gap-3 rounded-2xl border border-amber-900/40 bg-amber-950/10 p-4.5 text-xs text-amber-400 backdrop-blur-md">
              <AlertTriangle className="h-5 w-5 text-amber-400 flex-shrink-0 animate-bounce" />
              <div>
                <span className="font-extrabold uppercase tracking-wide text-[10px] px-1.5 py-0.5 rounded bg-amber-500/10 border border-amber-500/20 mr-1.5">
                  Alerta Estoque
                </span>
                Existem{' '}
                <span className="font-black underline">{stats.low_stock_items} insumos</span> abaixo
                do nível crítico de alerta. Verifique a seção de Estoque.
              </div>
            </div>
          )}

          {/* Charts Row */}
          <div className="grid gap-6 md:grid-cols-2">
            {/* Sales Trend Chart Card */}
            <div className="rounded-2xl border border-gray-900 bg-gray-950/10 p-5 space-y-5 backdrop-blur-md glass-card">
              <h3 className="text-xs font-black uppercase tracking-widest text-gray-500">
                Evolução do Faturamento
              </h3>
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
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Sales by Category Chart Card */}
            <div className="rounded-2xl border border-gray-900 bg-gray-950/10 p-5 space-y-5 backdrop-blur-md glass-card">
              <h3 className="text-xs font-black uppercase tracking-widest text-gray-500">
                Vendas por Categoria
              </h3>

              {categoryChartData.length === 0 ? (
                <div className="flex h-64 items-center justify-center text-xs text-gray-550 italic">
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

          {/* Kitchen KPIs Summary Panel */}
          {kitchenStats && (
            <div className="rounded-2xl border border-gray-900 bg-gray-950/10 p-5 backdrop-blur-md glass-card space-y-4">
              <h3 className="text-xs font-black uppercase tracking-widest text-gray-500">
                Produtividade da Cozinha
              </h3>
              <div className="grid gap-4 sm:grid-cols-3 text-center text-xs">
                <div className="border border-gray-900 bg-gray-950/20 rounded-xl p-4.5 space-y-1.5">
                  <span className="text-[10px] text-gray-550 uppercase font-extrabold tracking-wider">
                    Pratos Preparados
                  </span>
                  <div className="text-xl font-black text-white">{kitchenStats.items_prepared}</div>
                </div>
                <div className="border border-gray-900 bg-gray-950/20 rounded-xl p-4.5 space-y-1.5">
                  <span className="text-[10px] text-gray-550 uppercase font-extrabold tracking-wider">
                    Taxa de Conclusão
                  </span>
                  <div className="text-xl font-black text-emerald-400 flex items-center justify-center gap-1.5">
                    <CheckCircle className="h-4.5 w-4.5 text-emerald-500" />
                    <span>{(kitchenStats.completion_rate * 100).toFixed(0)}%</span>
                  </div>
                </div>
                <div className="border border-gray-900 bg-gray-950/20 rounded-xl p-4.5 space-y-1.5">
                  <span className="text-[10px] text-gray-550 uppercase font-extrabold tracking-wider">
                    Tempo Médio Fila
                  </span>
                  <div className="text-xl font-black text-blue-400">
                    {kitchenStats.average_prep_time_minutes.toFixed(1)}{' '}
                    <span className="text-xs font-medium text-gray-500">min</span>
                  </div>
                </div>
              </div>
            </div>
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
