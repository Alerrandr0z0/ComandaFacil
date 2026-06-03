import { AlertCircle, BellRing, Clock, Coffee, Plus } from 'lucide-react'
import { useEffect, useState } from 'react'
import { httpClient } from '@/shared/lib/http_client'
import type { ReadyItem } from '../hooks/use_kitchen_alerts'
import type { OrderForm } from '../hooks/use_order_drawer'

interface TableStatus {
  tableNumber: number
  order: OrderForm | null
  loading: boolean
  error: boolean
}

interface TableGridProps {
  onSelectTable: (tableNumber: number, order: OrderForm | null) => void
  selectedTableNumber: number | null
  readyItems: ReadyItem[]
  onDismissReadyItem: (itemId: number) => void
}

interface TableCardProps {
  tableNumber: number
  order: OrderForm | null
  loading: boolean
  error: boolean
  isOpening: boolean
  isSelected: boolean
  readyCount: number
  onOpenTable: (num: number) => void
  onSelectTable: (num: number, order: OrderForm | null) => void
  onClearReadyItems: () => void
}

interface StatusConfig {
  statusLabel: string
  statusColor: string
  borderGlow: string
}

function getTableStatusConfig(
  hasReadyAlert: boolean,
  isPaid: boolean,
  isPaymentRequested: boolean,
  isOccupied: boolean,
): StatusConfig {
  if (hasReadyAlert) {
    return {
      statusLabel: 'Prato Pronto!',
      statusColor: 'border-rose-500/30 bg-rose-950/20 text-rose-400 animate-pulse',
      borderGlow: 'border-rose-500/50 shadow-rose-950/30 animate-pulse-glow',
    }
  }
  if (isPaid) {
    return {
      statusLabel: 'Paga',
      statusColor: 'border-purple-500/25 bg-purple-950/10 text-purple-400',
      borderGlow: 'hover:border-purple-500/40 hover:shadow-purple-950/20',
    }
  }
  if (isPaymentRequested) {
    return {
      statusLabel: 'Conta Pedida',
      statusColor: 'border-blue-500/25 bg-blue-950/10 text-blue-400',
      borderGlow: 'hover:border-blue-500/40 hover:shadow-blue-950/20',
    }
  }
  if (isOccupied) {
    return {
      statusLabel: 'Ocupada',
      statusColor: 'border-amber-500/25 bg-amber-950/10 text-amber-400',
      borderGlow: 'hover:border-amber-500/40 hover:shadow-amber-950/20',
    }
  }
  return {
    statusLabel: 'Livre',
    statusColor: 'border-emerald-500/25 bg-emerald-950/10 text-emerald-400',
    borderGlow: 'hover:border-emerald-500/40 hover:shadow-emerald-950/20',
  }
}

function useElapsedTime(isOccupied: boolean, tableNumber: number): string {
  const [elapsedTime, setElapsedTime] = useState<string>('')

  useEffect(() => {
    if (!isOccupied) {
      setElapsedTime('')
      return
    }

    const key = `cf_table_${tableNumber}_open_time`
    let openTime = localStorage.getItem(key)
    if (!openTime) {
      openTime = Date.now().toString()
      localStorage.setItem(key, openTime)
    }

    const startTime = parseInt(openTime, 10)

    const updateTimer = () => {
      const diffMs = Date.now() - startTime
      const diffMins = Math.floor(diffMs / 60000)
      const diffSecs = Math.floor((diffMs % 60000) / 1000)

      const minStr = diffMins < 10 ? `0${diffMins}` : diffMins
      const secStr = diffSecs < 10 ? `0${diffSecs}` : diffSecs
      setElapsedTime(`${minStr}:${secStr}`)
    }

    updateTimer()
    const timer = setInterval(updateTimer, 1000)
    return () => clearInterval(timer)
  }, [isOccupied, tableNumber])

  return elapsedTime
}

interface TableCardDetailsProps {
  order: OrderForm | null
}

function TableCardDetails({ order }: TableCardDetailsProps) {
  if (!order) return null
  return (
    <div className="space-y-2 border-t border-gray-900/50 pt-3">
      <div className="flex items-center gap-1.5 text-[10px] text-gray-400 font-medium">
        <Coffee className="h-3.5 w-3.5 text-brand-400" />
        <span>{order.items.reduce((sum, item) => sum + item.quantity, 0)} itens pedidos</span>
      </div>
      <div className="text-xs font-black text-amber-500">
        Total: R$ {Number(order.total).toFixed(2)}
      </div>
    </div>
  )
}

interface TableCardActionsProps {
  loading: boolean
  isOccupied: boolean
  isSelected: boolean
  isOpening: boolean
  tableNumber: number
  onOpenTable: (num: number) => void
}

function TableCardActions({
  loading,
  isOccupied,
  isSelected,
  isOpening,
  tableNumber,
  onOpenTable,
}: TableCardActionsProps) {
  if (loading) {
    return <div className="h-8 w-full rounded-xl bg-gray-900 animate-pulse" />
  }

  if (isOccupied) {
    return (
      <div
        className={`flex w-full items-center justify-center gap-1.5 rounded-xl py-2 text-xs font-extrabold transition-all duration-300 ${
          isSelected
            ? 'bg-brand-500 text-white shadow-md'
            : 'bg-white/[0.02] border border-gray-900 text-gray-300 hover:text-white hover:border-gray-800'
        }`}
      >
        Ver Comanda
      </div>
    )
  }

  return (
    <button
      type="button"
      disabled={isOpening}
      onClick={(e) => {
        e.stopPropagation()
        onOpenTable(tableNumber)
      }}
      className="flex w-full items-center justify-center gap-1.5 rounded-xl border border-gray-900/80 bg-gray-950/20 hover:border-brand-500/20 hover:bg-brand-950/5 py-2 text-xs font-extrabold text-gray-400 hover:text-brand-400 transition-all duration-300"
    >
      {isOpening ? (
        <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
      ) : (
        <>
          <Plus className="h-4 w-4" />
          Abrir Mesa
        </>
      )}
    </button>
  )
}

function TableCard({
  tableNumber,
  order,
  loading,
  error,
  isOpening,
  isSelected,
  readyCount,
  onOpenTable,
  onSelectTable,
  onClearReadyItems,
}: TableCardProps) {
  const isOccupied = order !== null
  const isPaymentRequested = !!order?.payment_requested
  const isPaid = order?.state === 'PAID'
  const hasReadyAlert = readyCount > 0

  const elapsedTime = useElapsedTime(isOccupied, tableNumber)

  const { statusLabel, statusColor, borderGlow } = getTableStatusConfig(
    hasReadyAlert,
    isPaid,
    isPaymentRequested,
    isOccupied,
  )

  const handleSelect = () => {
    if (!loading) {
      onSelectTable(tableNumber, order)
    }
  }

  return (
    <button
      type="button"
      onClick={handleSelect}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          handleSelect()
        }
      }}
      className={`relative flex flex-col justify-between rounded-2xl border p-5 backdrop-blur-md transition-all duration-300 shadow-md cursor-pointer w-full text-left ${
        isSelected
          ? 'border-brand-500 bg-brand-950/5 shadow-brand-950/25'
          : loading
            ? 'border-gray-900 bg-gray-950/20 opacity-70 animate-pulse'
            : `border-gray-900/60 bg-gray-950/15 ${borderGlow}`
      }`}
    >
      {/* Ready items notification alert */}
      {hasReadyAlert && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation()
            onClearReadyItems()
          }}
          className="absolute -top-2 -right-2 bg-rose-500 text-white rounded-full p-1.5 shadow-lg border border-rose-400 hover:bg-rose-600 active:scale-95 transition-all duration-200 z-10 flex items-center gap-1 text-[9px] font-black uppercase px-2 py-1"
          title="Entregar e dispensar alerta"
        >
          <BellRing className="h-3.5 w-3.5 animate-bounce" />
          <span>Servir ({readyCount})</span>
        </button>
      )}

      <div className="space-y-4 w-full">
        <div className="flex items-start justify-between">
          <span className="text-[10px] uppercase font-extrabold text-gray-500 tracking-wider">
            Mesa
          </span>
          <span
            className={`rounded-full px-2.5 py-0.5 text-[9px] font-extrabold uppercase tracking-widest border ${statusColor}`}
          >
            {loading ? 'Carregando' : statusLabel}
          </span>
        </div>

        <div className="flex items-baseline justify-between">
          <span className="text-3xl font-black text-white tracking-tight">
            {tableNumber < 10 ? `0${tableNumber}` : tableNumber}
          </span>
          {isOccupied && elapsedTime && (
            <div className="flex items-center gap-1 text-[10px] font-bold text-gray-400">
              <Clock className="h-3.5 w-3.5 text-gray-500" />
              <span>{elapsedTime}</span>
            </div>
          )}
        </div>

        <TableCardDetails order={order} />

        {error && (
          <div className="flex items-center gap-1.5 text-[10px] font-semibold text-rose-400">
            <AlertCircle className="h-3.5 w-3.5" />
            <span>Erro de conexão</span>
          </div>
        )}
      </div>

      <div className="mt-4 pt-3 border-t border-gray-900/60 w-full">
        <TableCardActions
          loading={loading}
          isOccupied={isOccupied}
          isSelected={isSelected}
          isOpening={isOpening}
          tableNumber={tableNumber}
          onOpenTable={onOpenTable}
        />
      </div>
    </button>
  )
}

export default function TableGrid({
  onSelectTable,
  selectedTableNumber,
  readyItems,
  onDismissReadyItem,
}: TableGridProps) {
  const [tables, setTables] = useState<TableStatus[]>([])
  const [isOpening, setIsOpening] = useState<number | null>(null)
  const [_refreshTrigger, setRefreshTrigger] = useState(0)

  // Load status of all tables
  useEffect(() => {
    const fetchTables = async () => {
      const count = parseInt(localStorage.getItem('cf_tables_count') || '12', 10)
      const initialTables: TableStatus[] = Array.from({ length: count }, (_, i) => ({
        tableNumber: i + 1,
        order: null,
        loading: true,
        error: false,
      }))
      setTables(initialTables)

      try {
        const promises = Array.from({ length: count }, (_, i) => {
          const num = i + 1
          return httpClient
            .get<OrderForm>(`/v1/order/${num}`)
            .then((res) => ({
              num,
              order: res.data.state === 'CLOSED' ? null : res.data,
              error: false,
            }))
            .catch((err) => {
              const errorObj = err as { response?: { status: number } }
              if (errorObj.response && errorObj.response.status === 404) {
                return { num, order: null, error: false }
              }
              return { num, order: null, error: true }
            })
        })

        const results = await Promise.all(promises)
        setTables(
          results.map(({ num, order, error }) => ({
            tableNumber: num,
            order,
            loading: false,
            error,
          })),
        )
      } catch (_err) {
        setTables((prev) => prev.map((t) => ({ ...t, loading: false, error: true })))
      }
    }

    fetchTables()
  }, [])

  const handleOpenTable = async (tableNumber: number) => {
    setIsOpening(tableNumber)
    try {
      const res = await httpClient.post<OrderForm>('/v1/order', {
        id: tableNumber,
        fulfillment_type: 'TABLE',
        table_number: tableNumber,
      })
      // Track opening timestamp locally
      localStorage.setItem(`cf_table_${tableNumber}_open_time`, Date.now().toString())
      setRefreshTrigger((prev) => prev + 1)
      onSelectTable(tableNumber, res.data)
    } catch (_err) {
      alert(`Falha ao abrir a mesa ${tableNumber}. Tente novamente.`)
    } finally {
      setIsOpening(null)
    }
  }

  // Count KDS ready items associated with each table
  const getReadyCountForTable = (_tableNum: number, order: OrderForm | null): number => {
    if (!order) return 0
    // Get all item IDs currently confirmed in the order
    const orderItemIds = order.items.map((item) => item.id)
    // Filter readyItems where correlation_id corresponds to any order item id
    return readyItems.filter((item) => orderItemIds.includes(item.correlation_id)).length
  }

  const handleClearTableReadyAlerts = (_tableNum: number, order: OrderForm | null) => {
    if (!order) return
    const orderItemIds = order.items.map((item) => item.id)
    const matchingItems = readyItems.filter((item) => orderItemIds.includes(item.correlation_id))

    // Dismiss all matching alerts
    for (const item of matchingItems) {
      onDismissReadyItem(item.id)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between border-b border-gray-900/60 pb-3">
        <div>
          <h2 className="text-lg font-black text-white tracking-wide uppercase">Salão / Mesas</h2>
          <p className="text-xs text-gray-550 font-medium mt-0.5">
            Gerencie a ocupação das mesas e atenda comandas
          </p>
        </div>
        <button
          type="button"
          onClick={() => setRefreshTrigger((prev) => prev + 1)}
          className="rounded-xl bg-gray-900/30 border border-gray-850 hover:border-gray-700 px-4 py-2 text-xs font-bold text-gray-300 hover:text-white transition-all duration-300"
        >
          Atualizar Painel
        </button>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
        {tables.map((table) => {
          const readyCount = getReadyCountForTable(table.tableNumber, table.order)
          return (
            <TableCard
              key={table.tableNumber}
              tableNumber={table.tableNumber}
              order={table.order}
              loading={table.loading}
              error={table.error}
              isSelected={selectedTableNumber === table.tableNumber}
              isOpening={isOpening === table.tableNumber}
              readyCount={readyCount}
              onOpenTable={handleOpenTable}
              onSelectTable={onSelectTable}
              onClearReadyItems={() => handleClearTableReadyAlerts(table.tableNumber, table.order)}
            />
          )
        })}
      </div>
    </div>
  )
}
