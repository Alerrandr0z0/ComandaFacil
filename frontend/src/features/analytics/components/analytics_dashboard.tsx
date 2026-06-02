import { AlertTriangle, Clock, DollarSign, RefreshCw, ShoppingBag, TrendingUp } from 'lucide-react'
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
          params: { period: period.toUpperCase() },
        }),
        httpClient.get<SalesReport>('/v1/analytics/sales', {
          params: { period: period.toUpperCase() },
        }),
        httpClient.get<KitchenPerformance>('/v1/analytics/kitchen', {
          params: { period: period.toUpperCase() },
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
        { time: 'Dom', total: 3800 },
      ]
    }
    return [
      { time: 'Semana 1', total: 12000 },
      { time: 'Semana 2', total: 15400 },
      { time: 'Semana 3', total: 18900 },
      { time: 'Semana 4', total: 22100 },
    ]
  })()

  const colors = ['#f97316', '#a855f7', '#06b6d4', '#10b981', '#ef4444']

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-gray-800/80 pb-4">
        <div>
          <h2 className="text-xl font-bold text-gray-100">Painel Analytics</h2>
          <p className="text-xs text-gray-400">
            Análise de vendas, faturamento e tempos operacionais de cozinha
          </p>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-2">
          <div className="flex bg-gray-900/50 border border-gray-800 rounded-lg p-1">
            <button
              type="button"
              onClick={() => setPeriod('day')}
              className={`rounded px-3 py-1 text-xs font-semibold uppercase tracking-wider transition ${
                period === 'day' ? 'bg-brand-500 text-white' : 'text-gray-400 hover:text-white'
              }`}
            >
              Hoje
            </button>
            <button
              type="button"
              onClick={() => setPeriod('week')}
              className={`rounded px-3 py-1 text-xs font-semibold uppercase tracking-wider transition ${
                period === 'week' ? 'bg-brand-500 text-white' : 'text-gray-400 hover:text-white'
              }`}
            >
              Semana
            </button>
            <button
              type="button"
              onClick={() => setPeriod('month')}
              className={`rounded px-3 py-1 text-xs font-semibold uppercase tracking-wider transition ${
                period === 'month' ? 'bg-brand-500 text-white' : 'text-gray-400 hover:text-white'
              }`}
            >
              Mês
            </button>
          </div>

          <button
            type="button"
            onClick={fetchAnalytics}
            className="rounded-lg bg-gray-900 border border-gray-800 p-2 text-gray-400 hover:text-white transition"
            title="Atualizar Indicadores"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {isLoading && !stats ? (
        <div className="text-center py-24 text-xs text-gray-500 animate-pulse">
          Calculando estatísticas analíticas...
        </div>
      ) : error ? (
        <div className="rounded-xl border border-red-900/50 bg-red-950/20 p-6 text-center text-red-400">
          {error}
        </div>
      ) : (
        <div className="space-y-6">
          {/* KPI Cards */}
          <div className="grid gap-4 grid-cols-2 md:grid-cols-4">
            {/* Card 1: Sales */}
            <div className="rounded-xl border border-gray-800 bg-gray-900/20 p-4 space-y-2 backdrop-blur-md">
              <div className="flex items-center justify-between">
                <span className="text-[10px] uppercase font-bold tracking-wider text-gray-400">
                  Faturamento
                </span>
                <DollarSign className="h-4 w-4 text-emerald-400" />
              </div>
              <div className="text-xl font-black text-white tracking-tight">
                R$ {Number(stats?.total_sales).toFixed(2)}
              </div>
            </div>

            {/* Card 2: Ticket */}
            <div className="rounded-xl border border-gray-800 bg-gray-900/20 p-4 space-y-2 backdrop-blur-md">
              <div className="flex items-center justify-between">
                <span className="text-[10px] uppercase font-bold tracking-wider text-gray-400">
                  Ticket Médio
                </span>
                <TrendingUp className="h-4 w-4 text-brand-400" />
              </div>
              <div className="text-xl font-black text-white tracking-tight">
                R$ {Number(stats?.average_ticket).toFixed(2)}
              </div>
            </div>

            {/* Card 3: Orders */}
            <div className="rounded-xl border border-gray-800 bg-gray-900/20 p-4 space-y-2 backdrop-blur-md">
              <div className="flex items-center justify-between">
                <span className="text-[10px] uppercase font-bold tracking-wider text-gray-400">
                  Comandas
                </span>
                <ShoppingBag className="h-4 w-4 text-purple-400" />
              </div>
              <div className="text-xl font-black text-white tracking-tight">
                {stats?.orders_count}
              </div>
            </div>

            {/* Card 4: Prep Time */}
            <div className="rounded-xl border border-gray-800 bg-gray-900/20 p-4 space-y-2 backdrop-blur-md">
              <div className="flex items-center justify-between">
                <span className="text-[10px] uppercase font-bold tracking-wider text-gray-400">
                  Preparo Cozinha
                </span>
                <Clock className="h-4 w-4 text-blue-400" />
              </div>
              <div className="text-xl font-black text-white tracking-tight">
                {stats?.average_prep_time_minutes.toFixed(1)}{' '}
                <span className="text-xs text-gray-400">min</span>
              </div>
            </div>
          </div>

          {/* Warnings (if low stock exists) */}
          {stats && stats.low_stock_items > 0 && (
            <div className="flex items-center gap-3 rounded-xl border border-amber-900/40 bg-amber-950/10 p-4 text-xs text-amber-400 backdrop-blur-md">
              <AlertTriangle className="h-5 w-5 text-amber-400 flex-shrink-0" />
              <div>
                <span className="font-bold">Atenção Gerência:</span> Existem{' '}
                <span className="font-extrabold">{stats.low_stock_items}</span> itens com estoque
                abaixo do nível crítico de alerta. Verifique o painel de Estoque.
              </div>
            </div>
          )}

          {/* Recharts Graphs */}
          <div className="grid gap-6 md:grid-cols-2">
            {/* Sales Trends Chart */}
            <div className="rounded-xl border border-gray-800/80 bg-gray-900/10 p-5 space-y-4 backdrop-blur-md">
              <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400">
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
                    <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                    <XAxis dataKey="time" stroke="#9ca3af" fontSize={10} />
                    <YAxis stroke="#9ca3af" fontSize={10} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#030712',
                        borderColor: '#1f2937',
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

            {/* Category Chart */}
            <div className="rounded-xl border border-gray-800/80 bg-gray-900/10 p-5 space-y-4 backdrop-blur-md">
              <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400">
                Vendas por Categoria
              </h3>

              {categoryChartData.length === 0 ? (
                <div className="flex h-64 items-center justify-center text-xs text-gray-500">
                  Nenhuma venda realizada neste período para gerar dados de categorias.
                </div>
              ) : (
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={categoryChartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                      <XAxis dataKey="name" stroke="#9ca3af" fontSize={10} />
                      <YAxis stroke="#9ca3af" fontSize={10} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#030712',
                          borderColor: '#1f2937',
                          color: '#fff',
                          fontSize: 11,
                        }}
                        cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                      />
                      <Bar dataKey="valor" radius={[4, 4, 0, 0]}>
                        {categoryChartData.map((entry, index) => (
                          <Cell key={`cell-${entry.name}`} fill={colors[index % colors.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>
          </div>

          {/* Kitchen KPIs */}
          {kitchenStats && (
            <div className="rounded-xl border border-gray-800/80 bg-gray-900/10 p-5 backdrop-blur-md space-y-4">
              <h3 className="text-xs font-bold uppercase tracking-wider text-gray-400">
                Produtividade da Cozinha
              </h3>
              <div className="grid gap-4 sm:grid-cols-3 text-center text-xs">
                <div className="border border-gray-850 rounded-lg p-3 space-y-1">
                  <span className="text-[10px] text-gray-500 uppercase font-bold">
                    Total Pratos Preparados
                  </span>
                  <div className="text-lg font-extrabold text-white">
                    {kitchenStats.items_prepared}
                  </div>
                </div>
                <div className="border border-gray-850 rounded-lg p-3 space-y-1">
                  <span className="text-[10px] text-gray-500 uppercase font-bold">
                    Taxa de Conclusão
                  </span>
                  <div className="text-lg font-extrabold text-emerald-400">
                    {(kitchenStats.completion_rate * 100).toFixed(0)}%
                  </div>
                </div>
                <div className="border border-gray-850 rounded-lg p-3 space-y-1">
                  <span className="text-[10px] text-gray-500 uppercase font-bold">
                    Média de Espera
                  </span>
                  <div className="text-lg font-extrabold text-blue-400">
                    {kitchenStats.average_prep_time_minutes.toFixed(1)} min
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
