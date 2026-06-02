import { AlertCircle, Coffee, Plus } from 'lucide-react'
import { useEffect, useState } from 'react'
import { httpClient } from '@/shared/lib/http_client'

interface OrderFulfillment {
  type: string | null
  fee: string
  table_number?: number | null
}

interface OrderItem {
  id: number
  menu_item_id: number
  name_cpy: string
  price_cpy: number
  quantity: number
  notes: string
  subtotal: number
}

interface OrderForm {
  id: number
  tenant_id: string
  state: 'OPEN' | 'PAID' | 'CLOSED'
  payment_requested: boolean
  total: number
  fulfillment: OrderFulfillment
  items: OrderItem[]
}

interface TableStatus {
  tableNumber: number
  order: OrderForm | null
  loading: boolean
  error: boolean
}

interface TableGridProps {
  onSelectTable: (tableNumber: number, order: OrderForm | null) => void
}

interface TableCardProps {
  tableNumber: number
  order: OrderForm | null
  loading: boolean
  error: boolean
  isOpening: boolean
  onOpenTable: (num: number) => void
  onSelectTable: (num: number, order: OrderForm | null) => void
}

function TableCard({
  tableNumber,
  order,
  loading,
  error,
  isOpening,
  onOpenTable,
  onSelectTable,
}: TableCardProps) {
  const isOccupied = order !== null
  const isPaymentRequested = order?.payment_requested
  const isPaid = order?.state === 'PAID'

  let statusLabel = 'Livre'
  let statusColor = 'border-emerald-500/30 bg-emerald-950/10 text-emerald-400'
  let glowColor = 'hover:border-emerald-500/50 hover:shadow-emerald-950/20'

  if (isPaid) {
    statusLabel = 'Paga'
    statusColor = 'border-purple-500/30 bg-purple-950/10 text-purple-400'
    glowColor = 'hover:border-purple-500/50 hover:shadow-purple-950/20'
  } else if (isPaymentRequested) {
    statusLabel = 'Conta Solicitada'
    statusColor = 'border-blue-500/30 bg-blue-950/10 text-blue-400'
    glowColor = 'hover:border-blue-500/50 hover:shadow-blue-950/20'
  } else if (isOccupied) {
    statusLabel = 'Ocupada'
    statusColor = 'border-amber-500/30 bg-amber-950/10 text-amber-400'
    glowColor = 'hover:border-amber-500/50 hover:shadow-amber-950/20'
  }

  return (
    <div
      className={`relative flex flex-col justify-between rounded-xl border p-4 backdrop-blur-md transition-all duration-300 shadow-md ${
        loading
          ? 'border-gray-900 bg-gray-950/20 opacity-70 animate-pulse'
          : `border-gray-800 bg-gray-900/30 ${glowColor}`
      }`}
    >
      <div className="space-y-3">
        <div className="flex items-start justify-between">
          <span className="text-sm font-semibold text-gray-400">Mesa</span>
          <span
            className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider border ${statusColor}`}
          >
            {loading ? 'Carregando' : statusLabel}
          </span>
        </div>

        <div className="flex items-baseline gap-1">
          <span className="text-3xl font-black text-white tracking-tight">
            {tableNumber < 10 ? `0${tableNumber}` : tableNumber}
          </span>
        </div>

        {isOccupied && order && (
          <div className="space-y-1.5">
            <div className="flex items-center gap-1.5 text-[11px] text-gray-400">
              <Coffee className="h-3 w-3 text-brand-400" />
              <span>{order.items.length} itens pedidos</span>
            </div>
            <div className="text-xs font-bold text-amber-500">
              Total: R$ {Number(order.total).toFixed(2)}
            </div>
          </div>
        )}

        {error && (
          <div className="flex items-center gap-1 text-[11px] text-red-400">
            <AlertCircle className="h-3 w-3" />
            <span>Erro de conexão</span>
          </div>
        )}
      </div>

      <div className="mt-4 pt-3 border-t border-gray-800/60">
        {loading ? (
          <div className="h-8 w-full rounded-lg bg-gray-800 animate-pulse" />
        ) : isOccupied ? (
          <button
            type="button"
            onClick={() => onSelectTable(tableNumber, order)}
            className="flex w-full items-center justify-center gap-1.5 rounded-lg bg-brand-500 hover:bg-brand-600 active:scale-[0.98] py-2 text-xs font-bold text-white transition duration-200"
          >
            Ver Comanda
          </button>
        ) : (
          <button
            type="button"
            disabled={isOpening}
            onClick={() => onOpenTable(tableNumber)}
            className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-gray-800 hover:border-brand-500/30 hover:bg-brand-950/10 active:scale-[0.98] py-2 text-xs font-bold text-gray-300 hover:text-brand-400 transition duration-200"
          >
            {isOpening ? (
              <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
            ) : (
              <>
                <Plus className="h-3.5 w-3.5" />
                Abrir Mesa
              </>
            )}
          </button>
        )}
      </div>
    </div>
  )
}

const tableNumbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

export default function TableGrid({ onSelectTable }: TableGridProps) {
  const [tables, setTables] = useState<TableStatus[]>(
    tableNumbers.map((num) => ({
      tableNumber: num,
      order: null,
      loading: true,
      error: false,
    })),
  )
  const [_refreshTrigger, setRefreshTrigger] = useState(0)
  const [isOpening, setIsOpening] = useState<number | null>(null)

  useEffect(() => {
    let active = true
    // Reference _refreshTrigger to satisfy dependency linting
    void _refreshTrigger

    async function fetchTableStatuses() {
      const promises = tableNumbers.map(async (num) => {
        try {
          const res = await httpClient.get<OrderForm>(`/v1/order/${num}`)
          if (res.data.state === 'CLOSED') {
            return { tableNumber: num, order: null, loading: false, error: false }
          }
          return { tableNumber: num, order: res.data, loading: false, error: false }
        } catch (err) {
          const errorObj = err as { response?: { status: number } }
          if (errorObj.response && errorObj.response.status === 404) {
            return { tableNumber: num, order: null, loading: false, error: false }
          }
          return { tableNumber: num, order: null, loading: false, error: true }
        }
      })

      const results = await Promise.all(promises)
      if (active) {
        setTables(results)
      }
    }

    fetchTableStatuses()

    const interval = setInterval(fetchTableStatuses, 10000)

    return () => {
      active = false
      clearInterval(interval)
    }
  }, [_refreshTrigger])

  const handleOpenTable = async (tableNumber: number) => {
    setIsOpening(tableNumber)
    try {
      const res = await httpClient.post<OrderForm>('/v1/order', {
        id: tableNumber,
        fulfillment_type: 'TABLE',
        table_number: tableNumber,
      })
      setRefreshTrigger((prev) => prev + 1)
      onSelectTable(tableNumber, res.data)
    } catch (_err) {
      alert(`Falha ao abrir a mesa ${tableNumber}. Tente novamente.`)
    } finally {
      setIsOpening(null)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-100">Painel de Mesas</h2>
          <p className="text-xs text-gray-400">Gerencie a ocupação do salão e atenda comandas</p>
        </div>
        <button
          type="button"
          onClick={() => setRefreshTrigger((prev) => prev + 1)}
          className="rounded-lg bg-gray-900 border border-gray-800 hover:border-gray-700 px-3 py-1.5 text-xs text-gray-300 transition hover:text-white"
        >
          Atualizar Salão
        </button>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
        {tables.map((table) => (
          <TableCard
            key={table.tableNumber}
            tableNumber={table.tableNumber}
            order={table.order}
            loading={table.loading}
            error={table.error}
            isOpening={isOpening === table.tableNumber}
            onOpenTable={handleOpenTable}
            onSelectTable={onSelectTable}
          />
        ))}
      </div>
    </div>
  )
}
