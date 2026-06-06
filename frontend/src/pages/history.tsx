import {
  AlertTriangle,
  Eye,
  History as HistoryIcon,
  MapPin,
  Receipt,
  RefreshCcw,
  Search,
  User,
  X,
} from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useAuth } from '@/features/auth/auth_context'
import Layout from '@/shared/components/layout'
import { httpClient } from '@/shared/lib/http_client'

interface OrderHistoryItem {
  id?: number
  name: string
  price: string
  quantity: number
  station_type: string
  subtotal: string
  notes?: string
}

interface OrderHistory {
  order_id: number
  tenant_id: string
  total: string
  state: 'PAID' | 'CLOSED' | 'REFUNDED' | string
  fulfillment: {
    type: 'TABLE' | 'TAKEAWAY' | 'DELIVERY' | null
    fee: string
    table?: {
      table_number: number
    }
    takeaway?: {
      customer_name: string
    }
    delivery?: {
      street: string
      number: string
      neighborhood: string
      city: string
      state: string
      postal_code: string
      estimated_time: number
      tracking_code?: number
      delivery_state?: string
    }
  }
  items: OrderHistoryItem[]
  closed_at: string
}

interface StatsProps {
  totalSales: number
  completedCount: number
  refundCount: number
  totalRefunded: number
}

function SalesMetricsCards({ stats, filteredCount }: { stats: StatsProps; filteredCount: number }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <div className="p-4 rounded-2xl border border-gray-900/60 bg-gray-950/15 backdrop-blur-md flex flex-col justify-between">
        <span className="text-[10px] uppercase font-extrabold text-gray-550 tracking-wider">
          Total Faturado
        </span>
        <div className="mt-2 flex items-baseline gap-1">
          <span className="text-xs font-bold text-gray-400">R$</span>
          <span className="text-xl font-black text-white">
            {stats.totalSales.toLocaleString('pt-BR', {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}
          </span>
        </div>
        <span className="text-[9px] text-emerald-400 font-bold mt-1">
          {stats.completedCount} comandas encerradas
        </span>
      </div>

      <div className="p-4 rounded-2xl border border-gray-900/60 bg-gray-950/15 backdrop-blur-md flex flex-col justify-between">
        <span className="text-[10px] uppercase font-extrabold text-gray-550 tracking-wider">
          Total Estornado
        </span>
        <div className="mt-2 flex items-baseline gap-1">
          <span className="text-xs font-bold text-gray-400">R$</span>
          <span className="text-xl font-black text-rose-400">
            {stats.totalRefunded.toLocaleString('pt-BR', {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}
          </span>
        </div>
        <span className="text-[9px] text-rose-400/80 font-bold mt-1">
          {stats.refundCount} vendas devolvidas
        </span>
      </div>

      <div className="p-4 rounded-2xl border border-gray-900/60 bg-gray-950/15 backdrop-blur-md flex flex-col justify-between">
        <span className="text-[10px] uppercase font-extrabold text-gray-550 tracking-wider">
          Ticket Médio
        </span>
        <div className="mt-2 flex items-baseline gap-1">
          <span className="text-xs font-bold text-gray-400">R$</span>
          <span className="text-xl font-black text-amber-500">
            {(stats.completedCount > 0
              ? stats.totalSales / stats.completedCount
              : 0
            ).toLocaleString('pt-BR', {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}
          </span>
        </div>
        <span className="text-[9px] text-gray-500 font-medium mt-1">
          Faturamento / Comandas pagas
        </span>
      </div>

      <div className="p-4 rounded-2xl border border-gray-900/60 bg-gray-950/15 backdrop-blur-md flex flex-col justify-between">
        <span className="text-[10px] uppercase font-extrabold text-gray-550 tracking-wider">
          Volume Filtrado
        </span>
        <div className="mt-2">
          <span className="text-xl font-black text-brand-400">{filteredCount}</span>
          <span className="text-xs text-gray-500 font-bold ml-1.5">vendas</span>
        </div>
        <span className="text-[9px] text-gray-500 font-medium mt-1">
          Resultado dos filtros atuais
        </span>
      </div>
    </div>
  )
}

function OrderDetailPanel({
  selectedOrder,
  onClose,
  employeeRole,
  isRefunding,
  refundConfirmId,
  setRefundConfirmId,
  onRefund,
  formatDate,
  formatFulfillmentType,
}: {
  selectedOrder: OrderHistory
  onClose: () => void
  employeeRole: string | null | undefined
  isRefunding: boolean
  refundConfirmId: number | null
  setRefundConfirmId: (id: number | null) => void
  onRefund: (orderId: number) => Promise<void>
  formatDate: (d: string) => string
  formatFulfillmentType: (t: string | null) => string
}) {
  return (
    <div className="border border-gray-900/60 rounded-2xl bg-gray-950/20 p-5 backdrop-blur-md glass-card space-y-5 sticky top-6">
      <div className="flex items-center justify-between border-b border-gray-900 pb-3">
        <div>
          <h3 className="text-sm font-bold text-white uppercase tracking-wider">
            Comanda #{selectedOrder.order_id}
          </h3>
          <p className="text-[10px] text-gray-550 font-medium mt-0.5">
            Fechada em: {formatDate(selectedOrder.closed_at)}
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded-lg p-1 hover:bg-gray-900 text-gray-500 hover:text-white transition"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="bg-[#0b0b11] border border-gray-850 p-3.5 rounded-xl space-y-3">
        <div className="flex items-center justify-between text-xs">
          <span className="text-gray-400">Status do Faturamento:</span>
          <span
            className={`text-[9px] px-2 py-0.5 rounded-full border uppercase tracking-wider font-extrabold ${
              selectedOrder.state === 'REFUNDED'
                ? 'border-rose-500/20 bg-rose-950/10 text-rose-400'
                : 'border-emerald-500/20 bg-emerald-950/10 text-emerald-400'
            }`}
          >
            {selectedOrder.state === 'REFUNDED' ? 'Estornado' : 'Pago'}
          </span>
        </div>

        <div className="flex items-center justify-between text-xs border-t border-gray-900/60 pt-2.5">
          <span className="text-gray-400">Modalidade:</span>
          <span className="font-bold text-white">
            {formatFulfillmentType(selectedOrder.fulfillment.type)}
          </span>
        </div>

        {selectedOrder.fulfillment.type === 'TABLE' && selectedOrder.fulfillment.table && (
          <div className="flex items-center justify-between text-xs pt-1.5">
            <span className="text-gray-400">Número da Mesa:</span>
            <span className="font-bold text-brand-400">
              Mesa {selectedOrder.fulfillment.table.table_number}
            </span>
          </div>
        )}

        {selectedOrder.fulfillment.type === 'TAKEAWAY' && selectedOrder.fulfillment.takeaway && (
          <div className="flex items-center justify-between text-xs pt-1.5">
            <span className="text-gray-400 flex items-center gap-1">
              <User className="h-3 w-3 text-gray-500" />
              Cliente (Retirada):
            </span>
            <span className="font-bold text-gray-200">
              {selectedOrder.fulfillment.takeaway.customer_name}
            </span>
          </div>
        )}

        {selectedOrder.fulfillment.type === 'DELIVERY' && selectedOrder.fulfillment.delivery && (
          <div className="border-t border-gray-900/60 pt-2.5 space-y-2 text-xs">
            <span className="text-gray-400 flex items-center gap-1">
              <MapPin className="h-3 w-3 text-brand-400" />
              Endereço de Entrega:
            </span>
            <div className="text-[10px] text-gray-400 bg-gray-950/40 p-2.5 rounded-lg border border-gray-900 leading-relaxed">
              <p className="font-bold text-gray-200">
                {selectedOrder.fulfillment.delivery.street},{' '}
                {selectedOrder.fulfillment.delivery.number}
              </p>
              <p>
                {selectedOrder.fulfillment.delivery.neighborhood} —{' '}
                {selectedOrder.fulfillment.delivery.city}/{selectedOrder.fulfillment.delivery.state}
              </p>
              <p className="text-[9px] text-gray-500 mt-1">
                CEP: {selectedOrder.fulfillment.delivery.postal_code}
              </p>
              <p className="text-[9px] text-amber-500 font-bold mt-1">
                Estimativa: {selectedOrder.fulfillment.delivery.estimated_time} min
              </p>
            </div>
          </div>
        )}
      </div>

      <div className="space-y-2.5">
        <h4 className="text-[10px] uppercase font-extrabold tracking-wider text-gray-500 flex items-center gap-1">
          <Receipt className="h-3.5 w-3.5 text-gray-600" />
          Itens Consumidos
        </h4>

        <div className="space-y-2 max-h-[220px] overflow-y-auto pr-1">
          {selectedOrder.items.map((item, idx) => (
            <div
              key={item.id || idx}
              className="p-2.5 rounded-lg bg-gray-950/30 border border-gray-900 flex justify-between gap-2.5 text-[11px]"
            >
              <div className="min-w-0 flex-1">
                <p className="font-bold text-gray-300 truncate">{item.name}</p>
                <p className="text-[9px] text-gray-500 mt-0.5">
                  {item.quantity}x R$ {parseFloat(item.price).toFixed(2)}
                </p>
                {item.notes && (
                  <p className="text-[9px] text-amber-500/80 italic mt-1 bg-amber-950/5 px-1.5 py-0.5 rounded border border-amber-950/20">
                    Obs: {item.notes}
                  </p>
                )}
              </div>
              <div className="text-right self-center font-bold text-gray-200">
                R$ {parseFloat(item.subtotal).toFixed(2)}
              </div>
            </div>
          ))}
        </div>

        <div className="border-t border-gray-900/60 pt-3 space-y-2 text-xs">
          {parseFloat(selectedOrder.fulfillment.fee) > 0 && (
            <div className="flex justify-between text-gray-400">
              <span>Taxa de Serviço/Entrega:</span>
              <span>R$ {parseFloat(selectedOrder.fulfillment.fee).toFixed(2)}</span>
            </div>
          )}
          <div className="flex justify-between text-sm font-black pt-1">
            <span className="text-white">Total Pago:</span>
            <span className="text-emerald-400">
              R$ {parseFloat(selectedOrder.total).toFixed(2)}
            </span>
          </div>
        </div>
      </div>

      {employeeRole === 'MANAGER' && selectedOrder.state !== 'REFUNDED' && (
        <div className="border-t border-gray-900/60 pt-4">
          {refundConfirmId === selectedOrder.order_id ? (
            <div className="p-3 bg-rose-950/15 border border-rose-950/40 rounded-xl space-y-3">
              <div className="flex gap-2 text-rose-400">
                <AlertTriangle className="h-4.5 w-4.5 shrink-0" />
                <div>
                  <p className="text-xs font-bold leading-normal">Confirmar Estorno?</p>
                  <p className="text-[9px] text-rose-400/80 mt-0.5 leading-normal">
                    Esta ação devolverá o valor integral e alterará o status da venda para
                    reembolsada de forma definitiva.
                  </p>
                </div>
              </div>
              <div className="flex gap-2.5">
                <button
                  type="button"
                  onClick={() => setRefundConfirmId(null)}
                  disabled={isRefunding}
                  className="flex-1 rounded-lg border border-gray-800 bg-gray-900 text-gray-400 hover:text-white py-1.5 text-[10px] font-bold transition"
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  onClick={() => onRefund(selectedOrder.order_id)}
                  disabled={isRefunding}
                  className="flex-1 rounded-lg bg-rose-600 hover:bg-rose-700 text-white py-1.5 text-[10px] font-bold transition flex items-center justify-center gap-1"
                >
                  {isRefunding ? (
                    <span className="h-3 w-3 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  ) : null}
                  Confirmar
                </button>
              </div>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setRefundConfirmId(selectedOrder.order_id)}
              className="w-full py-2.5 rounded-xl border border-rose-950/40 bg-rose-950/10 hover:bg-rose-900/20 text-rose-400 font-bold text-xs transition flex items-center justify-center gap-1.5"
            >
              <AlertTriangle className="h-4 w-4" />
              Estornar Faturamento
            </button>
          )}
        </div>
      )}
    </div>
  )
}

const isWithinPeriod = (closedAtStr: string, period: 'today' | 'week' | 'month' | 'all') => {
  if (period === 'all') return true
  const closedDate = new Date(closedAtStr)
  const now = new Date()

  if (period === 'today') {
    return closedDate.toDateString() === now.toDateString()
  }

  const diffDays = (now.getTime() - closedDate.getTime()) / (1000 * 3600 * 24)
  if (period === 'week') return diffDays <= 7
  if (period === 'month') return diffDays <= 30
  return true
}

const matchesSearchTerm = (item: OrderHistory, term: string) => {
  if (!term) return true
  const normalized = term.toLowerCase()
  return (
    String(item.order_id).includes(normalized) ||
    (item.fulfillment.takeaway?.customer_name || '').toLowerCase().includes(normalized) ||
    (item.fulfillment.table?.table_number !== undefined &&
      String(item.fulfillment.table.table_number).includes(normalized)) ||
    item.total.includes(normalized)
  )
}

export default function HistoryPage() {
  const { employee } = useAuth()
  const [history, setHistory] = useState<OrderHistory[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [periodFilter, setPeriodFilter] = useState<'today' | 'week' | 'month' | 'all'>('all')
  const [selectedOrder, setSelectedOrder] = useState<OrderHistory | null>(null)
  const [isRefunding, setIsRefunding] = useState(false)
  const [refundConfirmId, setRefundConfirmId] = useState<number | null>(null)

  const fetchHistory = useCallback(async () => {
    setIsLoading(true)
    try {
      const res = await httpClient.get<OrderHistory[]>('/v1/order/history/all')
      const sorted = (res.data || []).sort(
        (a, b) => new Date(b.closed_at).getTime() - new Date(a.closed_at).getTime(),
      )
      setHistory(sorted)
    } catch (_err) {
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchHistory()
  }, [fetchHistory])

  const handleRefund = async (orderId: number) => {
    setIsRefunding(true)
    try {
      await httpClient.post('/v1/payments/refund', { order_id: orderId })

      setHistory((prev) =>
        prev.map((item) => (item.order_id === orderId ? { ...item, state: 'REFUNDED' } : item)),
      )

      if (selectedOrder && selectedOrder.order_id === orderId) {
        setSelectedOrder((prev) => (prev ? { ...prev, state: 'REFUNDED' } : null))
      }

      setRefundConfirmId(null)
      alert(`Venda #${orderId} estornada com sucesso!`)
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } }
      const msg = error.response?.data?.detail || 'Erro ao processar o estorno de pagamento.'
      alert(`Falha no estorno: ${msg}`)
    } finally {
      setIsRefunding(false)
    }
  }

  const filteredHistory = useMemo(() => {
    return history.filter(
      (item) => matchesSearchTerm(item, searchTerm) && isWithinPeriod(item.closed_at, periodFilter),
    )
  }, [history, searchTerm, periodFilter])

  const stats = useMemo(() => {
    let totalSales = 0
    let refundCount = 0
    let totalRefunded = 0
    let completedCount = 0

    for (const item of filteredHistory) {
      const amount = parseFloat(item.total) || 0
      if (item.state === 'REFUNDED') {
        refundCount++
        totalRefunded += amount
      } else {
        completedCount++
        totalSales += amount
      }
    }

    return {
      totalSales,
      completedCount,
      refundCount,
      totalRefunded,
    }
  }, [filteredHistory])

  const formatFulfillmentType = (type: string | null) => {
    switch (type) {
      case 'TABLE':
        return 'Mesa'
      case 'TAKEAWAY':
        return 'Retirada'
      case 'DELIVERY':
        return 'Entrega'
      default:
        return 'Não definido'
    }
  }

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString)
      return date.toLocaleString('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      })
    } catch {
      return dateString
    }
  }

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between border-b border-gray-900/60 pb-4 gap-4">
          <div>
            <h2 className="text-lg font-black text-white tracking-wide uppercase flex items-center gap-2">
              <HistoryIcon className="h-5 w-5 text-brand-400" />
              Histórico de Vendas
            </h2>
            <p className="text-xs text-gray-550 font-medium mt-0.5">
              Auditoria de comandas fechadas, detalhes de consumo e estornos de faturamento
            </p>
          </div>
          <button
            type="button"
            onClick={fetchHistory}
            className="self-start sm:self-auto rounded-xl bg-gray-950/40 hover:bg-gray-900 border border-gray-900 px-3.5 py-2 text-xs font-bold text-gray-400 hover:text-white transition flex items-center gap-1.5"
          >
            <RefreshCcw className="h-3.5 w-3.5" />
            Atualizar
          </button>
        </div>

        <SalesMetricsCards stats={stats} filteredCount={filteredHistory.length} />

        <div className="p-4 rounded-2xl border border-gray-900/60 bg-gray-950/20 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
            <input
              type="text"
              placeholder="Buscar por ID, mesa, cliente..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full rounded-xl pl-10 pr-4 py-2.5 text-xs text-white glass-input"
            />
            {searchTerm && (
              <button
                type="button"
                onClick={() => setSearchTerm('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>

          <div className="flex bg-[#0b0b11] border border-gray-850 p-1 rounded-xl self-start md:self-auto">
            {(['today', 'week', 'month', 'all'] as const).map((period) => (
              <button
                key={period}
                type="button"
                onClick={() => setPeriodFilter(period)}
                className={`rounded-lg px-3 py-1.5 text-xs font-bold transition-all duration-300 ${
                  periodFilter === period
                    ? 'bg-brand-500 text-white'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                {period === 'today'
                  ? 'Hoje'
                  : period === 'week'
                    ? '7 Dias'
                    : period === 'month'
                      ? '30 Dias'
                      : 'Tudo'}
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <div className="xl:col-span-2 space-y-4">
            <div className="overflow-hidden border border-gray-900/60 rounded-2xl bg-gray-950/10 backdrop-blur-md shadow-lg shadow-black/10">
              {isLoading ? (
                <div className="py-20 flex flex-col items-center justify-center space-y-3">
                  <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-500 border-t-transparent" />
                  <p className="text-xs text-gray-550 italic">Buscando histórico de vendas...</p>
                </div>
              ) : filteredHistory.length === 0 ? (
                <div className="py-20 text-center space-y-2">
                  <Receipt className="h-8 w-8 text-gray-600 mx-auto" />
                  <p className="text-xs text-gray-550 italic">
                    Nenhum registro de venda encontrado para os filtros.
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="border-b border-gray-900 bg-gray-950/40 text-[10px] uppercase font-extrabold text-gray-400 tracking-wider">
                        <th className="py-3.5 px-4">Comanda ID</th>
                        <th className="py-3.5 px-4">Horário</th>
                        <th className="py-3.5 px-4">Modalidade</th>
                        <th className="py-3.5 px-4">Status</th>
                        <th className="py-3.5 px-4 text-right">Total</th>
                        <th className="py-3.5 px-4 text-center">Ações</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-900/40 text-xs">
                      {filteredHistory.map((item) => (
                        <tr
                          key={item.order_id}
                          onClick={() => setSelectedOrder(item)}
                          className={`hover:bg-white/[0.02] transition cursor-pointer ${
                            selectedOrder?.order_id === item.order_id
                              ? 'bg-brand-500/5 border-l-2 border-l-brand-500'
                              : ''
                          }`}
                        >
                          <td className="py-4 px-4 font-bold text-gray-200">#{item.order_id}</td>
                          <td className="py-4 px-4 text-gray-400">{formatDate(item.closed_at)}</td>
                          <td className="py-4 px-4">
                            <span className="font-semibold text-gray-300">
                              {formatFulfillmentType(item.fulfillment.type)}
                            </span>
                            {item.fulfillment.type === 'TABLE' && item.fulfillment.table && (
                              <span className="text-[10px] text-gray-500 ml-1">
                                (Mesa {item.fulfillment.table.table_number})
                              </span>
                            )}
                            {item.fulfillment.type === 'TAKEAWAY' && item.fulfillment.takeaway && (
                              <span className="text-[10px] text-gray-500 ml-1 block max-w-[120px] truncate">
                                {item.fulfillment.takeaway.customer_name}
                              </span>
                            )}
                          </td>
                          <td className="py-4 px-4">
                            <span
                              className={`text-[9px] px-2 py-0.5 rounded-full border uppercase tracking-wider font-extrabold ${
                                item.state === 'REFUNDED'
                                  ? 'border-rose-500/20 bg-rose-950/10 text-rose-400'
                                  : 'border-emerald-500/20 bg-emerald-950/10 text-emerald-400'
                              }`}
                            >
                              {item.state === 'REFUNDED' ? 'Estornado' : 'Pago'}
                            </span>
                          </td>
                          <td className="py-4 px-4 text-right font-black text-white">
                            R$ {parseFloat(item.total).toFixed(2)}
                          </td>
                          <td className="py-4 px-4 text-center">
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation()
                                setSelectedOrder(item)
                              }}
                              className="rounded-lg p-1.5 text-gray-400 hover:text-white hover:bg-gray-900 transition"
                              title="Ver Detalhes"
                            >
                              <Eye className="h-4 w-4" />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>

          <div className="xl:col-span-1">
            {selectedOrder ? (
              <OrderDetailPanel
                selectedOrder={selectedOrder}
                onClose={() => setSelectedOrder(null)}
                employeeRole={employee?.role}
                isRefunding={isRefunding}
                refundConfirmId={refundConfirmId}
                setRefundConfirmId={setRefundConfirmId}
                onRefund={handleRefund}
                formatDate={formatDate}
                formatFulfillmentType={formatFulfillmentType}
              />
            ) : (
              <div className="border border-dashed border-gray-850 rounded-2xl p-12 text-center text-xs text-gray-500 italic min-h-[300px] flex items-center justify-center sticky top-6">
                Selecione uma comanda no histórico para visualizar os detalhes.
              </div>
            )}
          </div>
        </div>
      </div>
    </Layout>
  )
}
