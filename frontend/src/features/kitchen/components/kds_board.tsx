import {
  BookOpen,
  Check,
  Clock,
  Flame,
  GlassWater,
  Loader2,
  Play,
  RefreshCw,
  X,
} from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useTenant } from '@/shared/hooks/useTenant'
import { formatDuration } from '@/shared/lib/format_duration'
import { httpClient } from '@/shared/lib/http_client'

interface KitchenItem {
  id: number
  correlation_id: number
  name_cpy: string
  station_type_cpy: string
  state: 'WAITING' | 'PREPARING' | 'READY' | 'CANCELLED' | 'CANCEL_REQUESTED' | 'SURPLUS'
  previous_state?: 'PREPARING' | 'READY'
  tenant_id?: string
  kitchen_item_id?: number
  preparation_profile?: 'STANDARD' | 'NO_PREP'
  notes?: string
  created_at?: string
  started_at?: string
  menu_item_id?: number
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
  onApproveCancel?: (itemId: number, mode: 'WASTE' | 'SURPLUS') => void
  onRejectCancel?: (itemId: number) => void
  seenTimestamps: Record<number, number>
  onShowRecipe?: (menuItemId: number, itemName: string) => void
}

function KdsItemActions({
  item,
  showCancel,
  actionLabel,
  onAction,
  onReady,
  onCancel,
  onApproveCancel,
  onRejectCancel,
  isCancelRequested,
}: {
  item: KitchenItem
  showCancel?: boolean
  actionLabel?: string
  onAction?: (itemId: number) => void
  onReady?: (itemId: number) => void
  onCancel?: (itemId: number) => void
  onApproveCancel?: (itemId: number, mode: 'WASTE' | 'SURPLUS') => void
  onRejectCancel?: (itemId: number) => void
  isCancelRequested: boolean
}) {
  if (isCancelRequested && onApproveCancel && onRejectCancel) {
    return (
      <div className="flex gap-1.5 flex-1 justify-end">
        <button
          type="button"
          onClick={() => onRejectCancel(item.id)}
          className="rounded-xl px-2.5 py-2 border border-gray-800 bg-gray-900 hover:bg-gray-850 text-gray-300 font-bold text-[10px] uppercase tracking-wider transition active:scale-[0.98]"
        >
          Recusar
        </button>
        <button
          type="button"
          onClick={() => onApproveCancel(item.id, 'SURPLUS')}
          className="rounded-xl px-2.5 py-2 bg-emerald-650 hover:bg-emerald-600 text-white font-bold text-[10px] uppercase tracking-wider shadow-md shadow-emerald-950/20 transition active:scale-[0.98]"
        >
          Sobra
        </button>
        <button
          type="button"
          onClick={() => onApproveCancel(item.id, 'WASTE')}
          className="rounded-xl px-2.5 py-2 bg-rose-650 hover:bg-rose-600 text-white font-bold text-[10px] uppercase tracking-wider shadow-md shadow-rose-950/20 transition active:scale-[0.98]"
        >
          Descarte
        </button>
      </div>
    )
  }

  return (
    <>
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
    </>
  )
}

function KdsItemCard({
  item,
  showCancel,
  actionLabel,
  onAction,
  onReady,
  onCancel,
  onApproveCancel,
  onRejectCancel,
  startTime,
  onShowRecipe,
}: {
  item: KitchenItem
  showCancel?: boolean
  actionLabel?: string
  onAction?: (itemId: number) => void
  onReady?: (itemId: number) => void
  onCancel?: (itemId: number) => void
  onApproveCancel?: (itemId: number, mode: 'WASTE' | 'SURPLUS') => void
  onRejectCancel?: (itemId: number) => void
  startTime: number
  onShowRecipe?: (menuItemId: number, itemName: string) => void
}) {
  const [elapsed, setElapsed] = useState('')

  useEffect(() => {
    const updateTimer = () => {
      const diffMs = Math.max(0, Date.now() - startTime)
      setElapsed(formatDuration(diffMs))
    }

    updateTimer()
    const interval = setInterval(updateTimer, 1000)
    return () => clearInterval(interval)
  }, [startTime])

  const isWarning = Date.now() - startTime > 10 * 60000 // > 10 mins
  const isCancelRequested = item.state === 'CANCEL_REQUESTED'

  return (
    <div
      className={`flex flex-col justify-between rounded-xl border p-4 space-y-4 transition-all duration-300 ${
        isCancelRequested
          ? 'border-rose-500 bg-rose-950/10 hover:border-rose-450 shadow-md shadow-rose-950/25 animate-pulse'
          : isWarning
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
        {item.menu_item_id && onShowRecipe && (
          <button
            type="button"
            onClick={() => item.menu_item_id && onShowRecipe(item.menu_item_id, item.name_cpy)}
            className="rounded-xl p-2.5 border border-gray-900 bg-gray-950/40 hover:bg-gray-900/40 text-gray-450 hover:text-white transition"
            title="Ver receita"
          >
            <BookOpen className="h-4 w-4" />
          </button>
        )}
        <KdsItemActions
          item={item}
          showCancel={showCancel}
          actionLabel={actionLabel}
          onAction={onAction}
          onReady={onReady}
          onCancel={onCancel}
          onApproveCancel={onApproveCancel}
          onRejectCancel={onRejectCancel}
          isCancelRequested={isCancelRequested}
        />
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
  onApproveCancel,
  onRejectCancel,
  seenTimestamps,
  onShowRecipe,
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
              onApproveCancel={onApproveCancel}
              onRejectCancel={onRejectCancel}
              startTime={
                item.state === 'PREPARING' && item.started_at
                  ? new Date(item.started_at).getTime()
                  : item.created_at
                    ? new Date(item.created_at).getTime()
                    : seenTimestamps[item.id] || Date.now()
              }
              onShowRecipe={onShowRecipe}
            />
          ))
        )}
      </div>
    </div>
  )
}

interface RecipeIngredient {
  stock_item_id: number
  stock_item_name: string
  quantity_value: number
  quantity_unit: string
}

interface RecipeData {
  menu_item_id: number
  ingredients: RecipeIngredient[]
}

function RecipeModal({
  menuItemId,
  itemName,
  onClose,
}: {
  menuItemId: number
  itemName: string
  onClose: () => void
}) {
  const [recipe, setRecipe] = useState<RecipeData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    const fetchRecipe = async () => {
      try {
        const res = await httpClient.get<RecipeData>(`/v1/stock/recipes/${menuItemId}`)
        if (active) {
          setRecipe(res.data)
        }
      } catch (_err) {
        if (active) {
          setError('Nenhuma receita cadastrada para este item.')
        }
      } finally {
        if (active) {
          setIsLoading(false)
        }
      }
    }
    fetchRecipe()
    return () => {
      active = false
    }
  }, [menuItemId])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="w-full max-w-md rounded-2xl border border-gray-900 bg-gray-950 p-6 shadow-2xl relative animate-in zoom-in-95 duration-200">
        <button
          type="button"
          onClick={onClose}
          className="absolute top-4 right-4 rounded-xl p-1.5 text-gray-400 hover:text-white hover:bg-white/[0.05] transition"
        >
          <X className="h-5 w-5" />
        </button>

        <div className="flex items-center gap-2.5 mb-5 border-b border-gray-900 pb-3">
          <BookOpen className="h-5 w-5 text-brand-400" />
          <h3 className="text-base font-black text-white uppercase tracking-wide">
            Receita: {itemName}
          </h3>
        </div>

        {isLoading ? (
          <div className="flex py-10 justify-center items-center gap-2">
            <Loader2 className="h-5 w-5 animate-spin text-brand-400" />
            <span className="text-xs text-gray-400 font-medium">Carregando ingredientes...</span>
          </div>
        ) : error ? (
          <div className="py-6 text-center text-xs text-gray-500 font-medium italic">{error}</div>
        ) : (
          <div className="space-y-3">
            <h4 className="text-xs font-bold text-gray-400 uppercase tracking-widest text-left">
              Ingredientes
            </h4>
            <div className="divide-y divide-gray-900 overflow-hidden rounded-xl border border-gray-900 bg-gray-950/20">
              {recipe?.ingredients.map((ing) => (
                <div
                  key={ing.stock_item_id}
                  className="flex justify-between items-center px-4 py-3 hover:bg-white/[0.01] transition-colors"
                >
                  <span className="text-sm font-medium text-white">{ing.stock_item_name}</span>
                  <span className="text-xs font-black text-brand-400 bg-brand-500/10 border border-brand-500/20 rounded-lg px-2.5 py-1">
                    {ing.quantity_value} {ing.quantity_unit}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="mt-6 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl bg-gray-900 hover:bg-gray-850 px-4 py-2.5 text-xs font-bold text-white transition active:scale-95"
          >
            Fechar
          </button>
        </div>
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
  const [selectedRecipe, setSelectedRecipe] = useState<{ id: number; name: string } | null>(null)

  // Track timestamps of when items are first seen to show elapsed timers locally
  const [seenTimestamps, setSeenTimestamps] = useState<Record<number, number>>({})
  const wsRef = useRef<WebSocket | null>(null)

  const fetchItems = useCallback(async () => {
    setError(null)
    try {
      const res = await httpClient.get<KitchenItem[]>('/v1/kitchen/items', {
        params: { station_type: stationType },
      })

      const data = res.data.map((item: KitchenItem) => ({
        ...item,
        id: item.kitchen_item_id ?? item.id,
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

  const handleApproveCancel = async (itemId: number, mode: 'WASTE' | 'SURPLUS') => {
    try {
      await httpClient.post(`/v1/kitchen/items/${itemId}/cancel/approve`, { mode })
      fetchItems()
    } catch (_err) {
      alert('Erro ao aprovar o cancelamento.')
    }
  }

  const handleRejectCancel = async (itemId: number) => {
    try {
      await httpClient.post(`/v1/kitchen/items/${itemId}/cancel/reject`)
      fetchItems()
    } catch (_err) {
      alert('Erro ao recusar o cancelamento.')
    }
  }

  const waitingItems = items.filter((item) => item.state === 'WAITING')
  const preparingItems = items.filter(
    (item) =>
      item.state === 'PREPARING' ||
      (item.state === 'CANCEL_REQUESTED' && item.previous_state === 'PREPARING'),
  )
  const readyItems = items.filter(
    (item) =>
      item.state === 'READY' ||
      (item.state === 'CANCEL_REQUESTED' && item.previous_state === 'READY'),
  )
  const surplusItems = items.filter((item) => item.state === 'SURPLUS')

  const handleShowRecipe = (menuItemId: number, itemName: string) => {
    setSelectedRecipe({ id: menuItemId, name: itemName })
  }

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
        <div className="grid gap-6 grid-cols-1 md:grid-cols-2 lg:grid-cols-4">
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
            onShowRecipe={handleShowRecipe}
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
            onApproveCancel={handleApproveCancel}
            onRejectCancel={handleRejectCancel}
            seenTimestamps={seenTimestamps}
            onShowRecipe={handleShowRecipe}
          />
          <KdsColumn
            title="Prontos p/ Retirada"
            count={readyItems.length}
            colorClass="text-emerald-400"
            items={readyItems}
            onApproveCancel={handleApproveCancel}
            onRejectCancel={handleRejectCancel}
            seenTimestamps={seenTimestamps}
            onShowRecipe={handleShowRecipe}
          />
          <KdsColumn
            title="Sobras (15 min)"
            count={surplusItems.length}
            colorClass="text-indigo-400"
            items={surplusItems}
            seenTimestamps={seenTimestamps}
            onShowRecipe={handleShowRecipe}
          />
        </div>
      )}

      {selectedRecipe && (
        <RecipeModal
          menuItemId={selectedRecipe.id}
          itemName={selectedRecipe.name}
          onClose={() => setSelectedRecipe(null)}
        />
      )}
    </div>
  )
}
