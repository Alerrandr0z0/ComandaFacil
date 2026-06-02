import { Check, Flame, GlassWater, Loader2, Play, RefreshCw, X } from 'lucide-react'
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
}

interface KdsColumnProps {
  title: string
  count: number
  colorClass: string
  items: KitchenItem[]
  showCancel?: boolean
  actionLabel?: string
  onAction?: (itemId: number) => void
  onCancel?: (itemId: number) => void
}

function KdsColumn({
  title,
  count,
  colorClass,
  items,
  showCancel = false,
  actionLabel,
  onAction,
  onCancel,
}: KdsColumnProps) {
  return (
    <div className="flex flex-col rounded-xl border border-gray-800/80 bg-gray-900/10 p-4">
      <h3
        className={`border-b border-gray-850 pb-3 text-sm font-bold uppercase tracking-wider ${colorClass} flex items-center justify-between`}
      >
        {title}
        <span className="rounded-full bg-gray-950/50 border border-gray-900/50 px-2 py-0.5 text-xs">
          {count}
        </span>
      </h3>

      <div className="mt-4 flex-1 space-y-3 overflow-y-auto max-h-[600px] pr-1">
        {items.length === 0 ? (
          <div className="py-12 text-center text-xs text-gray-500">Nenhum pedido nesta fila.</div>
        ) : (
          items.map((item) => (
            <div
              key={item.id}
              className={`flex flex-col justify-between rounded-lg border border-gray-800/35 bg-gray-950/10 p-3 space-y-3 transition hover:border-brand-500/20`}
            >
              <div>
                <div className="flex items-center justify-between text-[10px] text-gray-500">
                  <span>Ref ID: #{item.id}</span>
                </div>
                <h4 className="mt-1 text-sm font-bold text-gray-100">{item.name_cpy}</h4>
              </div>

              <div className="flex gap-2 justify-end">
                {showCancel && onCancel && (
                  <button
                    type="button"
                    onClick={() => onCancel(item.id)}
                    className="rounded-lg p-1.5 border border-red-900 bg-red-950/25 hover:bg-red-900/20 text-red-400 transition"
                    title="Cancelar item"
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
                {actionLabel && onAction && (
                  <button
                    type="button"
                    onClick={() => onAction(item.id)}
                    className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-bold text-white transition active:scale-[0.98] ${
                      item.state === 'WAITING'
                        ? 'bg-amber-500 hover:bg-amber-600'
                        : 'bg-blue-500 hover:bg-blue-600'
                    }`}
                  >
                    {item.state === 'WAITING' ? (
                      <Play className="h-3.5 w-3.5 fill-current" />
                    ) : (
                      <Check className="h-3.5 w-3.5" />
                    )}
                    {actionLabel}
                  </button>
                )}
              </div>
            </div>
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
  const wsRef = useRef<WebSocket | null>(null)

  const fetchItems = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const res = await httpClient.get<KitchenItem[]>('/v1/kitchen/items', {
        params: { station_type: stationType },
      })
      setItems(res.data)
    } catch (_err) {
      setError('Erro ao carregar itens da cozinha.')
    } finally {
      setIsLoading(false)
    }
  }, [stationType])

  useEffect(() => {
    fetchItems()
  }, [fetchItems])

  useEffect(() => {
    if (!tenantId) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//localhost:8000/api/v1/kitchen/ws?station_type=${stationType}&tenant_id=${tenantId}`

    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      setConnected(true)
    }

    ws.onmessage = () => {
      fetchItems()
    }

    ws.onerror = (_err) => {
      setConnected(false)
    }

    ws.onclose = () => {
      setConnected(false)
    }

    return () => {
      ws.close()
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

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-gray-800/80 pb-4">
        <div>
          <h2 className="text-xl font-bold text-gray-100 flex items-center gap-2">
            Painel KDS
            <span
              className={`inline-block h-2.5 w-2.5 rounded-full ${connected ? 'bg-emerald-500 shadow-sm shadow-emerald-500/20' : 'bg-red-500'} animate-pulse`}
              title={connected ? 'Conectado em tempo real' : 'Sem conexão WebSocket'}
            />
          </h2>
          <p className="text-xs text-gray-400">Monitoramento e despacho de pedidos da cozinha</p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setStationType('GRILL')}
            className={`flex items-center gap-1.5 rounded-lg px-4 py-2 text-xs font-semibold uppercase tracking-wider transition duration-300 ${
              stationType === 'GRILL'
                ? 'bg-brand-500 text-white shadow-md shadow-brand-500/10'
                : 'bg-gray-900/50 border border-gray-800 text-gray-400 hover:text-white'
            }`}
          >
            <Flame className="h-4 w-4" />
            Cozinha (Grill)
          </button>
          <button
            type="button"
            onClick={() => setStationType('BEVERAGE')}
            className={`flex items-center gap-1.5 rounded-lg px-4 py-2 text-xs font-semibold uppercase tracking-wider transition duration-300 ${
              stationType === 'BEVERAGE'
                ? 'bg-brand-500 text-white shadow-md shadow-brand-500/10'
                : 'bg-gray-900/50 border border-gray-800 text-gray-400 hover:text-white'
            }`}
          >
            <GlassWater className="h-4 w-4" />
            Copa (Bebidas)
          </button>
          <button
            type="button"
            onClick={fetchItems}
            className="rounded-lg bg-gray-900 border border-gray-800 p-2 text-gray-400 hover:text-white transition"
            title="Atualizar Pedidos"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>

      {isLoading && items.length === 0 ? (
        <div className="flex py-24 justify-center items-center gap-2">
          <Loader2 className="h-6 w-6 animate-spin text-brand-400" />
          <span className="text-xs text-gray-400">Carregando pedidos ativos...</span>
        </div>
      ) : error ? (
        <div className="rounded-xl border border-red-900/50 bg-red-950/20 p-6 text-center text-red-400">
          {error}
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-3">
          <KdsColumn
            title="Fila de Espera"
            count={waitingItems.length}
            colorClass="text-amber-400"
            items={waitingItems}
            showCancel={true}
            actionLabel="Preparar"
            onAction={handlePrepare}
            onCancel={handleCancel}
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
          />
          <KdsColumn
            title="Prontos p/ Retirada"
            count={readyItems.length}
            colorClass="text-emerald-400"
            items={readyItems}
          />
        </div>
      )}
    </div>
  )
}
