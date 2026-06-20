import { BellRing, Clock, Coffee, MapPin, ShoppingBag, User } from 'lucide-react'
import { useEffect, useState } from 'react'
import { httpClient } from '@/shared/lib/http_client'
import type { ReadyItem } from '../hooks/use_kitchen_alerts'
import type { OrderForm } from '../hooks/use_order_drawer'

interface ActiveOrder {
  order: OrderForm
  loading: boolean
  error: boolean
}

interface OrderGridProps {
  onSelectOrder: (orderId: number, order: OrderForm | null) => void
  selectedOrderId: number | null
  readyItems: ReadyItem[]
  onDismissReadyItem: (itemId: number) => void
  onNewOrder: () => void
  onActiveOrdersCount?: (count: number) => void
  refreshKey?: number
}

interface OrderCardProps {
  order: OrderForm
  isSelected: boolean
  readyCount: number
  onSelect: () => void
  onClearReadyItems: () => void
}

const FULFILLMENT_LABELS: Record<string, string> = {
  TABLE: 'Mesa',
  TAKEAWAY: 'Retirada',
  DELIVERY: 'Delivery',
}

function getStatusLabel(order: OrderForm): { label: string; color: string } {
  if (order.state === 'PAID') {
    return { label: 'Paga', color: 'border-purple-500/25 bg-purple-950/10 text-purple-400' }
  }
  if (order.payment_requested) {
    return { label: 'Conta Pedida', color: 'border-blue-500/25 bg-blue-950/10 text-blue-400' }
  }
  return { label: 'Aberta', color: 'border-amber-500/25 bg-amber-950/10 text-amber-400' }
}

function getFulfillmentLine(order: OrderForm): string {
  const f = order.fulfillment
  if (f.type === 'TABLE' && f.table_number) {
    return `Mesa ${f.table_number < 10 ? '0' : ''}${f.table_number}`
  }
  if (f.type === 'TAKEAWAY' && f.customer_name) {
    return f.customer_name
  }
  if (f.type === 'DELIVERY') {
    const parts = [f.delivery_street, f.delivery_number].filter(Boolean)
    return parts.join(', ') || 'Delivery'
  }
  return '—'
}

function getFulfillmentIcon(type: string | null) {
  switch (type) {
    case 'TABLE':
      return Coffee
    case 'TAKEAWAY':
      return User
    case 'DELIVERY':
      return MapPin
    default:
      return ShoppingBag
  }
}

function useElapsedTime(orderId: number): string {
  const [elapsedTime, setElapsedTime] = useState<string>('')

  useEffect(() => {
    const key = `cf_order_${orderId}_open_time`
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
  }, [orderId])

  return elapsedTime
}

function OrderCard({ order, isSelected, readyCount, onSelect, onClearReadyItems }: OrderCardProps) {
  const { label: statusLabel, color: statusColor } = getStatusLabel(order)
  const fulfillmentLine = getFulfillmentLine(order)
  const FulfillmentIcon = getFulfillmentIcon(order.fulfillment.type)
  const elapsedTime = useElapsedTime(order.id)
  const itemCount = order.items.reduce((sum, item) => sum + item.quantity, 0)
  const hasReadyAlert = readyCount > 0

  return (
    <button
      type="button"
      onClick={onSelect}
      className={`relative flex flex-col justify-between rounded-2xl border p-5 backdrop-blur-md transition-all duration-300 shadow-md cursor-pointer w-full text-left ${
        isSelected
          ? 'border-brand-500 bg-brand-950/5 shadow-brand-950/25'
          : 'border-gray-900/60 bg-gray-950/15 hover:border-brand-500/40 hover:shadow-brand-950/20'
      }`}
    >
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
          <div className="flex items-center gap-2">
            <FulfillmentIcon className="h-4 w-4 text-brand-400" />
            <span className="text-[10px] uppercase font-extrabold text-gray-500 tracking-wider">
              {FULFILLMENT_LABELS[order.fulfillment.type ?? ''] || 'Comanda'}
            </span>
          </div>
          <span
            className={`rounded-full px-2.5 py-0.5 text-[9px] font-extrabold uppercase tracking-widest border ${statusColor}`}
          >
            {statusLabel}
          </span>
        </div>

        <div className="flex items-baseline justify-between">
          <div className="space-y-0.5">
            <span className="text-3xl font-black text-white tracking-tight">
              {order.display_code || `#${order.id}`}
            </span>
            <p className="text-[11px] font-bold text-gray-400 text-left">{fulfillmentLine}</p>
          </div>
          {elapsedTime && (
            <div className="flex items-center gap-1 text-[10px] font-bold text-gray-400">
              <Clock className="h-3.5 w-3.5 text-gray-500" />
              <span>{elapsedTime}</span>
            </div>
          )}
        </div>
      </div>

      <div className="mt-4 pt-3 border-t border-gray-900/60 w-full space-y-2">
        <div className="flex items-center gap-1.5 text-[10px] text-gray-400 font-medium">
          <ShoppingBag className="h-3.5 w-3.5 text-brand-400" />
          <span>{itemCount} itens</span>
        </div>
        <div className="text-xs font-black text-amber-500">
          Total: R$ {Number(order.total).toFixed(2)}
        </div>
      </div>

      {order.fulfillment.type === 'DELIVERY' && order.fulfillment.delivery_estimated_time && (
        <div className="mt-2 text-[9px] font-semibold text-gray-500">
          Previsão: {order.fulfillment.delivery_estimated_time} min
        </div>
      )}
    </button>
  )
}

export default function OrderGrid({
  onSelectOrder,
  selectedOrderId,
  readyItems,
  onDismissReadyItem,
  onNewOrder,
  onActiveOrdersCount,
  refreshKey,
}: OrderGridProps) {
  const [orders, setOrders] = useState<ActiveOrder[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [refreshTrigger, setRefreshTrigger] = useState(0)

  // biome-ignore lint/correctness/useExhaustiveDependencies: refreshTrigger/refreshKey trigger polling
  useEffect(() => {
    const fetchOrders = async () => {
      setIsLoading(true)
      try {
        const res = await httpClient.get<OrderForm[]>('/v1/order')
        const rawData = Array.isArray(res.data) ? res.data : []
        setOrders(
          rawData.map((order) => ({
            order,
            loading: false,
            error: false,
          })),
        )
        onActiveOrdersCount?.(res.data.length)
      } catch (_err) {
        setOrders((prev) => (prev.length > 0 ? prev : []))
      } finally {
        setIsLoading(false)
      }
    }

    fetchOrders()
  }, [onActiveOrdersCount, refreshTrigger, refreshKey])

  useEffect(() => {
    const interval = setInterval(() => {
      setRefreshTrigger((prev) => prev + 1)
    }, 5000)
    return () => clearInterval(interval)
  }, [])

  const getReadyCountForOrder = (order: OrderForm): number => {
    const orderItemIds = order.items.map((item) => item.id)
    return readyItems.filter((item) => orderItemIds.includes(item.correlation_id)).length
  }

  const handleClearOrderReadyAlerts = (order: OrderForm) => {
    const orderItemIds = order.items.map((item) => item.id)
    const matchingItems = readyItems.filter((item) => orderItemIds.includes(item.correlation_id))
    for (const item of matchingItems) {
      onDismissReadyItem(item.id)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between border-b border-gray-900/60 pb-3">
        <div>
          <h2 className="text-lg font-black text-white tracking-wide uppercase">
            Salão / Comandas
          </h2>
          <p className="text-xs text-gray-550 font-medium mt-0.5">
            Gerencie as comandas ativas do estabelecimento
          </p>
        </div>
        <button
          type="button"
          onClick={onNewOrder}
          className="flex items-center gap-1.5 rounded-xl bg-brand-500 hover:bg-brand-600 px-4 py-2.5 text-xs font-bold text-white transition-all shadow-md shadow-brand-500/15"
        >
          + Nova Comanda
        </button>
      </div>

      {isLoading && orders.length === 0 ? (
        <div className="flex items-center justify-center py-20">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-500 border-t-transparent" />
        </div>
      ) : orders.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center space-y-3">
          <Coffee className="h-12 w-12 text-gray-600" />
          <p className="text-sm font-bold text-gray-400">Nenhuma comanda ativa</p>
          <p className="text-xs text-gray-600 max-w-xs">
            As comandas abertas aparecerão aqui. Crie uma nova comanda para começar.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {orders.map(({ order }) => {
            const readyCount = getReadyCountForOrder(order)
            return (
              <OrderCard
                key={order.id}
                order={order}
                isSelected={selectedOrderId === order.id}
                readyCount={readyCount}
                onSelect={() => onSelectOrder(order.id, order)}
                onClearReadyItems={() => handleClearOrderReadyAlerts(order)}
              />
            )
          })}
        </div>
      )}
    </div>
  )
}
