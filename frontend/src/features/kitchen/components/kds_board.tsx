import { Check, Clock, Flame, GlassWater, Loader2, Play, RefreshCw, X } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useTenant } from '@/shared/hooks/useTenant'
import { httpClient } from '@/shared/lib/http_client'

interface KitchenItem {
  id: number
  correlation_id: number
  name_cpy: string
  station_type_cpy: string
  state: 'WAITING' | 'PREPARING' | 'READY' | 'CANCELLED'
  tenant_id: string
  kitchen_item_id?: number
  preparation_profile?: 'STANDARD' | 'NO_PREP'
  notes?: string
}

interface KdsColumnProps {
  title: string
  count: number
  colorClass: string
  items: KitchenItem[]
  showCancel?: boolean
  actionLabel?: string
  onAction?: (itemId: number) => void
  onReady?: (itemId: number) => void
  onCancel?: (itemId: number) => void
  seenTimestamps: Record<number, number>
}

function KdsItemCard({
  item,
  showCancel,
  actionLabel,
  onAction,
  onReady,
  onCancel,
  startTime,
}: {
  item: KitchenItem
  showCancel?: boolean
  actionLabel?: string
  onAction?: (itemId: number) => void
  onReady?: (itemId: number) => void
  onCancel?: (itemId: number) => void
  startTime: number
}) {
  const [elapsed, setElapsed] = useState('')

  useEffect(() => {
    const updateTimer = () => {
      const diffMs = Date.now() - startTime
      const diffMins = Math.floor(diffMs / 60000)
      const diffSecs = Math.floor((diffMs % 60000) / 1000)
      setElapsed(`${diffMins}m ${diffSecs}s`)
    }

    updateTimer()
    const interval = setInterval(updateTimer, 1000)
    return () => clearInterval(interval)
  }, [startTime])

  const isWarning = Date.now() - startTime > 10 * 60000 // > 10 mins

  return (
    <div
      className={`flex flex-col justify-between rounded-xl border p-4 space-y-4 transition-all duration-300 ${
        isWarning
          ? 'border-rose-500/30 bg-rose-950/5 hover:border-rose-500/40 shadow-md shadow-rose-950/10'
          : 'border-gray-900 bg-gray-950/20 hover:border-gray-850'
      }`}
    >
      <div className="flex justify-between items-start">
        <div className="space-y-1">
          <span className="text-[9px] uppercase tracking-wider font-extrabold text-gray-500">
            Ref ID: #{item.id}
          </span>
          <h4 className="text-sm font-bold text-white">{item.name_cpy}</h4>
          {item.notes && (
            <span className="text-[10px] italic text-brand-400 font-medium block">
              Obs: {item.notes}
            </span>
          )}
        </div>
        <div
          className={`flex items-center gap-1 text-[10px] font-bold ${isWarning ? 'text-rose-400' : 'text-gray-400'}`}
        >
          <Clock className="h-3.5 w-3.5" />
          <span>{elapsed}</span>
        </div>
      </div>

      <div className="flex gap-2 justify-end border-t border-gray-900/50 pt-3">
        {showCancel && onCancel && (
          <button
            type="button"
            onClick={() => onCancel(item.id)}
            className="rounded-xl p-2.5 border border-red-950/40 bg-red-950/10 hover:bg-red-900/20 text-red-400 transition"
            title="Cancelar item"
          >
            <X className="h-4 w-4" />
          </button>
        )}
        {actionLabel && onAction && (
          <button
            type="button"
            onClick={() => {
              if (item.state === 'WAITING' && item.preparation_profile === 'NO_PREP' && onReady) {
                onReady(item.id)
              } else {
                onAction(item.id)
              }
            }}
            className={`flex items-center gap-1.5 rounded-xl px-4 py-2.5 text-xs font-bold text-white transition-all duration-300 active:scale-[0.98] ${
              item.state === 'WAITING'
                ? item.preparation_profile === 'NO_PREP'
                  ? 'bg-brand-500 hover:bg-brand-600 shadow-md shadow-brand-500/10'
                  : 'bg-amber-500 hover:bg-amber-600 shadow-md shadow-amber-500/10'
                : 'bg-brand-500 hover:bg-brand-600 shadow-md shadow-brand-500/10'
            }`}
          >
            {item.state === 'WAITING' && item.preparation_profile === 'NO_PREP' ? (
              <>
                <Check className="h-3.5 w-3.5" />
                <span>Pronto</span>
              </>
            ) : item.state === 'WAITING' ? (
              <>
                <Play className="h-3.5 w-3.5 fill-current" />
                <span>{actionLabel}</span>
              </>
            ) : (
              <>
                <Check className="h-3.5 w-3.5" />
                <span>{actionLabel}</span>
              </>
            )}
          </button>
        )}
      </div>
    </div>
  )
}

function KdsColumn({
  title,
  count,
  colorClass,
  items,
  showCancel = false,
  actionLabel,
  onAction,
  onReady,
  onCancel,
  seenTimestamps,
}: KdsColumnProps) {
  return (
    <div className="flex flex-col rounded-2xl border border-gray-900 bg-gray-950/10 p-5 backdrop-blur-md glass-card h-[calc(100vh-14rem)] min-h-[400px]">
      <h3
        className={`border-b border-gray-900/60 pb-3 text-xs font-black uppercase tracking-widest ${colorClass} flex items-center justify-between`}
      >
        <span>{title}</span>
        <span className="rounded-full bg-white/[0.03] border border-gray-900 px-2 py-0.5 text-xs font-bold">
          {count}
        </span>
      </h3>

      <div className="mt-4 flex-1 space-y-3 overflow-y-auto pr-1">
        {items.length === 0 ? (
          <div className="py-16 text-center text-xs text-gray-500 font-medium">
            Nenhum pedido nesta fila.
          </div>
        ) : (
          items.map((item) => (
            <KdsItemCard
              key={item.id}
              item={item}
              showCancel={showCancel}
              actionLabel={actionLabel}
              onAction={onAction}
              onReady={onReady}
              onCancel={onCancel}
              startTime={seenTimestamps[item.id] || Date.now()}
            />
          ))
        )}
      </div>
    </div>
  )
}

export default function KdsBoard() {
  const { tenantId } = useTenant()
  const [stationType, setStationType] = useState<'GRILL' | 'BEVERAGE'>('GRILL')
  const [items, setItems] = useState<KitchenItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [connected, setConnected] = useState(false)

  // Track timestamps of when items are first seen to show elapsed timers locally
  const [seenTimestamps, setSeenTimestamps] = useState<Record<number, number>>({})
  const wsRef = useRef<WebSocket | null>(null)

  const fetchItems = useCallback(async () => {
    setError(null)
    try {
      const res = await httpClient.get<KitchenItem[]>('/v1/kitchen/items', {
        params: { station_type: stationType },
      })

      const rawData = Array.isArray(res.data) ? res.data : []
      const data = rawData.map((item: KitchenItem) => ({
        ...item,
        id: item.id || (item.kitchen_item_id as number),
      }))

      // Update seen timestamps dictionary
      setSeenTimestamps((prev) => {
        const updated = { ...prev }
        const now = Date.now()
        for (const item of data) {
          if (!updated[item.id]) {
            updated[item.id] = now
          }
        }
        return updated
      })

      setItems(data)
    } catch (_err) {
      setError('Erro ao carregar itens da cozinha.')
    } finally {
      setIsLoading(false)
    }
  }, [stationType])

  useEffect(() => {
    setIsLoading(true)
    fetchItems()
  }, [fetchItems])

  useEffect(() => {
    if (!tenantId) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const wsUrl = `${protocol}//${host}/api/v1/kitchen/ws?station_type=${stationType}&tenant_id=${tenantId}`

    let retries = 0
    const maxRetries = 10
    let retryTimer: ReturnType<typeof setTimeout> | null = null
    let ws: WebSocket | null = null
    let disconnected = false

    const connect = () => {
      if (disconnected) return

      ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        retries = 0
        setConnected(true)
      }

      ws.onmessage = () => {
        fetchItems()
      }

      ws.onerror = () => {
        setConnected(false)
      }

      ws.onclose = () => {
        setConnected(false)
        if (disconnected) return

        retries += 1
        if (retries <= maxRetries) {
          const delay = Math.min(1000 * 2 ** retries, 30000)
          retryTimer = setTimeout(connect, delay)
        }
      }
    }

    connect()

    return () => {
      disconnected = true
      if (retryTimer) clearTimeout(retryTimer)
      if (ws) ws.close()
      wsRef.current = null
    }
  }, [stationType, tenantId, fetchItems])

  const handlePrepare = async (itemId: number) => {
    try {
      await httpClient.patch(`/v1/kitchen/items/${itemId}/prepare`)
      fetchItems()
    } catch (_err) {
      alert('Erro ao iniciar o preparo do item.')
    }
  }

  const handleReady = async (itemId: number) => {
    try {
      await httpClient.patch(`/v1/kitchen/items/${itemId}/ready`)
      fetchItems()
    } catch (_err) {
      alert('Erro ao concluir o preparo do item.')
    }
  }

  const handleCancel = async (itemId: number) => {
    if (!window.confirm('Deseja realmente CANCELAR este item da cozinha?')) {
      return
    }
    try {
      await httpClient.patch(`/v1/kitchen/items/${itemId}/cancel`)
      fetchItems()
    } catch (_err) {
      alert('Erro ao cancelar o item.')
    }
  }

  const waitingItems = items.filter((item) => item.state === 'WAITING')
  const preparingItems = items.filter((item) => item.state === 'PREPARING')
  const readyItems = items.filter((item) => item.state === 'READY')
  const cancelledItems = items.filter((item) => item.state === 'CANCELLED')

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-gray-900/60 pb-4">
        <div>
          <h2 className="text-lg font-black text-white tracking-wide uppercase flex items-center gap-2">
            <span>Monitor de Cozinha (KDS)</span>
            <span
              className={`inline-block h-2.5 w-2.5 rounded-full ${connected ? 'bg-emerald-500 shadow-lg shadow-emerald-500/20' : 'bg-red-500'} animate-pulse`}
              title={connected ? 'Conectado em tempo real' : 'Sem conexão WebSocket'}
            />
          </h2>
          <p className="text-xs text-gray-550 font-medium mt-0.5">
            Gerenciamento operacional e preparo de pedidos em tempo real
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setStationType('GRILL')}
            className={`flex items-center gap-1.5 rounded-xl px-4 py-2.5 text-xs font-bold uppercase tracking-wider transition-all duration-300 ${
              stationType === 'GRILL'
                ? 'bg-brand-500 text-white shadow-lg shadow-brand-500/15'
                : 'bg-white/[0.02] border border-gray-900 text-gray-400 hover:text-white'
            }`}
          >
            <Flame className="h-4 w-4" />
            Cozinha (Grill)
          </button>
          <button
            type="button"
            onClick={() => setStationType('BEVERAGE')}
            className={`flex items-center gap-1.5 rounded-xl px-4 py-2.5 text-xs font-bold uppercase tracking-wider transition-all duration-300 ${
              stationType === 'BEVERAGE'
                ? 'bg-brand-500 text-white shadow-lg shadow-brand-500/15'
                : 'bg-white/[0.02] border border-gray-900 text-gray-400 hover:text-white'
            }`}
          >
            <GlassWater className="h-4 w-4" />
            Copa (Bebidas)
          </button>
          <button
            type="button"
            onClick={fetchItems}
            className="rounded-xl bg-gray-900/30 border border-gray-850 p-2.5 text-gray-400 hover:text-white transition-all duration-300"
            title="Atualizar Pedidos"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {isLoading && items.length === 0 ? (
        <div className="flex py-24 justify-center items-center gap-2.5">
          <Loader2 className="h-6 w-6 animate-spin text-brand-400" />
          <span className="text-xs text-gray-400 font-medium">Carregando pedidos ativos...</span>
        </div>
      ) : error ? (
        <div className="rounded-2xl border border-red-950/40 bg-red-950/15 p-6 text-center text-red-400 text-xs font-bold">
          {error}
        </div>
      ) : (
        <div className="grid gap-6 grid-cols-1 md:grid-cols-2 xl:grid-cols-4">
          <KdsColumn
            title="Fila de Espera"
            count={waitingItems.length}
            colorClass="text-amber-400"
            items={waitingItems}
            showCancel={true}
            actionLabel="Preparar"
            onAction={handlePrepare}
            onReady={handleReady}
            onCancel={handleCancel}
            seenTimestamps={seenTimestamps}
          />
          <KdsColumn
            title="Em Preparação"
            count={preparingItems.length}
            colorClass="text-blue-400"
            items={preparingItems}
            showCancel={true}
            actionLabel="Pronto"
            onAction={handleReady}
            onCancel={handleCancel}
            seenTimestamps={seenTimestamps}
          />
          <KdsColumn
            title="Prontos p/ Retirada"
            count={readyItems.length}
            colorClass="text-emerald-400"
            items={readyItems}
            seenTimestamps={seenTimestamps}
          />
          <KdsColumn
            title="Cancelados (15 min)"
            count={cancelledItems.length}
            colorClass="text-rose-450"
            items={cancelledItems}
            seenTimestamps={seenTimestamps}
          />
        </div>
      )}
    </div>
  )
}
