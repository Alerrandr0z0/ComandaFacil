import { useQuery } from '@tanstack/react-query'
import { Activity, Award, Building, DollarSign } from 'lucide-react'
import type React from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { type AnalyticsItem, getGlobalAnalytics, getTenants, type Tenant } from './adminService'

const COLORS = ['#6366f1', '#a855f7', '#ec4899', '#3b82f6']

export const AdminDashboard: React.FC = () => {
  const { data: tenants, isLoading: loadingTenants } = useQuery({
    queryKey: ['tenants'],
    queryFn: getTenants,
  })

  const { data: analytics, isLoading: loadingAnalytics } = useQuery({
    queryKey: ['analytics'],
    queryFn: () => getGlobalAnalytics({ limit: 5 }),
  })

  const totalRevenue = Array.isArray(analytics)
    ? analytics.reduce((sum: number, a: AnalyticsItem) => sum + a.total_revenue, 0)
    : 0

  const activeTenantsCount = Array.isArray(tenants)
    ? tenants.filter((t: Tenant) => t.is_active).length
    : 0

  // Chart 1: Revenue by Franchise Name
  const revenueChartData =
    Array.isArray(analytics) && Array.isArray(tenants)
      ? analytics.map((a: AnalyticsItem) => {
          const tenant = tenants.find((t: Tenant) => String(t.id) === String(a._id))
          return {
            name: tenant ? tenant.name : `Franquia ${a._id}`,
            receita: a.total_revenue,
          }
        })
      : []

  // Chart 2: Plan distribution
  const plansDistribution = Array.isArray(tenants)
    ? tenants.reduce((acc: Record<string, number>, t: Tenant) => {
        acc[t.plan_type] = (acc[t.plan_type] || 0) + 1
        return acc
      }, {})
    : {}

  const planChartData = Object.entries(plansDistribution).map(([name, value]) => ({
    name: `Plano ${name}`,
    value,
  }))

  if (loadingTenants || loadingAnalytics) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-500 border-t-transparent" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Title section */}
      <div>
        <h1 className="text-2xl font-black tracking-tight text-white">Painel Geral</h1>
        <p className="text-xs font-medium text-gray-400 mt-1">
          Visão consolidada e métricas de desempenho de todas as franquias da rede.
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
        <div className="p-5 bg-gray-950/40 border border-gray-900/60 rounded-2xl backdrop-blur-md flex items-center justify-between shadow-lg shadow-brand-500/2">
          <div className="space-y-1">
            <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider">
              Receita Geral
            </h3>
            <p className="text-2xl font-black text-white">
              R${' '}
              {totalRevenue.toLocaleString('pt-BR', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </p>
          </div>
          <div className="h-10 w-10 rounded-xl bg-green-500/10 border border-green-500/20 text-green-400 flex items-center justify-center shadow-inner">
            <DollarSign className="h-5 w-5" />
          </div>
        </div>

        <div className="p-5 bg-gray-950/40 border border-gray-900/60 rounded-2xl backdrop-blur-md flex items-center justify-between shadow-lg shadow-brand-500/2">
          <div className="space-y-1">
            <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider">
              Total Franquias
            </h3>
            <p className="text-2xl font-black text-white">{tenants?.length || 0}</p>
          </div>
          <div className="h-10 w-10 rounded-xl bg-brand-500/10 border border-brand-500/20 text-brand-400 flex items-center justify-center shadow-inner">
            <Building className="h-5 w-5" />
          </div>
        </div>

        <div className="p-5 bg-gray-950/40 border border-gray-900/60 rounded-2xl backdrop-blur-md flex items-center justify-between shadow-lg shadow-brand-500/2">
          <div className="space-y-1">
            <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider">
              Franquias Ativas
            </h3>
            <p className="text-2xl font-black text-white">{activeTenantsCount}</p>
          </div>
          <div className="h-10 w-10 rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-400 flex items-center justify-center shadow-inner">
            <Activity className="h-5 w-5" />
          </div>
        </div>

        <div className="p-5 bg-gray-950/40 border border-gray-900/60 rounded-2xl backdrop-blur-md flex items-center justify-between shadow-lg shadow-brand-500/2">
          <div className="space-y-1">
            <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider">
              Plano Predominante
            </h3>
            <p className="text-2xl font-black text-white">
              {planChartData.length > 0
                ? planChartData
                    .reduce((prev, current) => (prev.value > current.value ? prev : current))
                    .name.replace('Plano ', '')
                : 'N/A'}
            </p>
          </div>
          <div className="h-10 w-10 rounded-xl bg-pink-500/10 border border-pink-500/20 text-pink-400 flex items-center justify-center shadow-inner">
            <Award className="h-5 w-5" />
          </div>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Revenue Ranking Chart */}
        <div className="p-5 bg-gray-950/40 border border-gray-900/60 rounded-2xl backdrop-blur-md flex flex-col shadow-lg">
          <h3 className="text-sm font-bold text-white mb-4">Ranking de Receita por Franquia</h3>
          <div className="h-72 w-full">
            {revenueChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={revenueChartData}
                  margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
                  <XAxis dataKey="name" stroke="#9ca3af" fontSize={10} tickLine={false} />
                  <YAxis stroke="#9ca3af" fontSize={10} tickLine={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#09090b',
                      borderColor: '#1f2937',
                      color: '#fff',
                      borderRadius: '12px',
                    }}
                    formatter={(value: unknown) => [
                      `R$ ${Number(typeof value === 'number' || typeof value === 'string' ? value : 0).toFixed(2)}`,
                      'Receita',
                    ]}
                  />
                  <Bar
                    dataKey="receita"
                    fill="url(#brandGradient)"
                    radius={[6, 6, 0, 0]}
                    barSize={36}
                  >
                    <defs>
                      <linearGradient id="brandGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#6366f1" />
                        <stop offset="100%" stopColor="#4f46e5" />
                      </linearGradient>
                    </defs>
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center text-xs text-gray-500">
                Nenhum dado de receita disponível.
              </div>
            )}
          </div>
        </div>

        {/* Subscription Plan Distribution Chart */}
        <div className="p-5 bg-gray-950/40 border border-gray-900/60 rounded-2xl backdrop-blur-md flex flex-col shadow-lg">
          <h3 className="text-sm font-bold text-white mb-4">
            Distribuição de Planos de Assinatura
          </h3>
          <div className="h-72 w-full flex flex-col md:flex-row items-center justify-center gap-4">
            {planChartData.length > 0 ? (
              <>
                <div className="h-48 w-48 flex-shrink-0">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={planChartData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={80}
                        paddingAngle={5}
                        dataKey="value"
                      >
                        {planChartData.map((entry, index) => (
                          <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#09090b',
                          borderColor: '#1f2937',
                          color: '#fff',
                          borderRadius: '12px',
                        }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="flex-1 flex flex-col justify-center space-y-2">
                  {planChartData.map((entry, index) => (
                    <div
                      key={entry.name}
                      className="flex items-center justify-between text-xs p-2 rounded-xl bg-gray-900/20 border border-gray-900/40"
                    >
                      <div className="flex items-center gap-2">
                        <span
                          className="h-2 w-2 rounded-full"
                          style={{ backgroundColor: COLORS[index % COLORS.length] }}
                        />
                        <span className="font-semibold text-gray-300">{entry.name}</span>
                      </div>
                      <span className="font-bold text-white">
                        {entry.value} {entry.value === 1 ? 'franquia' : 'franquias'}
                      </span>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="flex h-full items-center justify-center text-xs text-gray-500">
                Nenhuma franquia cadastrada.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
