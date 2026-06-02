import {
  AlertTriangle,
  FileSpreadsheet,
  History,
  Minus,
  Plus,
  PlusCircle,
  RotateCcw,
  Sliders,
  TrendingDown,
  X,
} from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { httpClient } from '@/shared/lib/http_client'

interface StockItem {
  id: number
  name: string
  category: string
  current_quantity_amount: number
  current_quantity_unit: string
  min_stock_level: number
  is_active: boolean
  is_low_stock: boolean
}

interface StockMovement {
  id: number
  stock_item_id: number
  movement_type: 'ADD' | 'DEDUCT' | 'ADJUST' | 'MIN_LEVEL'
  quantity_changed: number
  reason: string
  created_at: string
}

interface StockItemRowProps {
  item: StockItem
  onOpenAction: (item: StockItem, type: 'ADD' | 'DEDUCT' | 'ADJUST' | 'MIN_LEVEL') => void
  onViewHistory: (item: StockItem) => void
}

function StockItemRow({ item, onOpenAction, onViewHistory }: StockItemRowProps) {
  return (
    <tr className={`hover:bg-gray-900/20 transition ${item.is_low_stock ? 'bg-red-950/5' : ''}`}>
      <td className="px-4 py-3">
        <div className="font-bold text-white flex items-center gap-2">
          {item.name}
          {item.is_low_stock && (
            <span
              className="rounded bg-red-950/60 border border-red-900/40 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-red-400 flex items-center gap-1"
              title="Estoque abaixo do mínimo!"
            >
              <AlertTriangle className="h-2.5 w-2.5" />
              Crítico
            </span>
          )}
        </div>
        <span className="text-[10px] text-gray-500">ID: #{item.id}</span>
      </td>
      <td className="px-4 py-3 text-[10px] font-semibold text-gray-400">{item.category}</td>
      <td className="px-4 py-3 font-mono font-bold text-sm text-gray-200">
        {item.current_quantity_amount}{' '}
        <span className="text-xs text-gray-500">{item.current_quantity_unit}</span>
      </td>
      <td className="px-4 py-3 font-mono text-gray-400">
        {item.min_stock_level} {item.current_quantity_unit}
      </td>
      <td className="px-4 py-3 text-right space-x-1 whitespace-nowrap">
        <button
          type="button"
          onClick={() => onOpenAction(item, 'ADD')}
          className="p-1 rounded bg-gray-900 border border-gray-800 hover:border-emerald-500/30 hover:text-emerald-400 text-gray-400 transition"
          title="Entrada (+)"
        >
          <Plus className="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          onClick={() => onOpenAction(item, 'DEDUCT')}
          className="p-1 rounded bg-gray-900 border border-gray-800 hover:border-red-500/30 hover:text-red-400 text-gray-400 transition"
          title="Saída (-)"
        >
          <Minus className="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          onClick={() => onOpenAction(item, 'ADJUST')}
          className="p-1 rounded bg-gray-900 border border-gray-800 hover:border-blue-500/30 hover:text-blue-400 text-gray-400 transition"
          title="Ajustar Inventário"
        >
          <Sliders className="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          onClick={() => onOpenAction(item, 'MIN_LEVEL')}
          className="p-1 rounded bg-gray-900 border border-gray-800 hover:border-amber-500/30 hover:text-amber-400 text-gray-400 transition"
          title="Alterar Limiar Mínimo"
        >
          <TrendingDown className="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          onClick={() => onViewHistory(item)}
          className="p-1 rounded bg-gray-900 border border-gray-800 hover:border-purple-500/30 hover:text-purple-400 text-gray-400 transition"
          title="Histórico de Movimentação"
        >
          <History className="h-3.5 w-3.5" />
        </button>
      </td>
    </tr>
  )
}

interface StockTableProps {
  items: StockItem[]
  onOpenAction: (item: StockItem, type: 'ADD' | 'DEDUCT' | 'ADJUST' | 'MIN_LEVEL') => void
  onViewHistory: (item: StockItem) => void
}

function StockTable({ items, onOpenAction, onViewHistory }: StockTableProps) {
  return (
    <div className="rounded-xl border border-gray-800/80 bg-gray-900/10 overflow-hidden backdrop-blur-md">
      <table className="w-full border-collapse text-left text-xs text-gray-300">
        <thead className="bg-gray-950/60 text-gray-400 border-b border-gray-800/60 uppercase tracking-wider text-[10px] font-bold">
          <tr>
            <th className="px-4 py-3">Insumo</th>
            <th className="px-4 py-3">Categoria</th>
            <th className="px-4 py-3">Quantidade</th>
            <th className="px-4 py-3">Nível Mínimo</th>
            <th className="px-4 py-3 text-right">Ações</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-850">
          {items.map((item) => (
            <StockItemRow
              key={item.id}
              item={item}
              onOpenAction={onOpenAction}
              onViewHistory={onViewHistory}
            />
          ))}
        </tbody>
      </table>
    </div>
  )
}

interface StockActionCardProps {
  actionType: 'ADD' | 'DEDUCT' | 'ADJUST' | 'MIN_LEVEL'
  actionValue: string
  actionReason: string
  onChangeValue: (val: string) => void
  onChangeReason: (val: string) => void
  onClose: () => void
  onSubmit: () => void
}

function StockActionCard({
  actionType,
  actionValue,
  actionReason,
  onChangeValue,
  onChangeReason,
  onClose,
  onSubmit,
}: StockActionCardProps) {
  return (
    <div className="rounded-xl border border-brand-500/30 bg-brand-950/5 p-4 backdrop-blur-md space-y-4">
      <div className="flex items-center justify-between border-b border-gray-855 pb-2">
        <h3 className="text-xs font-bold uppercase tracking-wider text-brand-400">
          {actionType === 'ADD'
            ? 'Registrar Entrada'
            : actionType === 'DEDUCT'
              ? 'Registrar Retirada'
              : actionType === 'ADJUST'
                ? 'Ajuste Físico'
                : 'Alterar Limite Alerta'}
        </h3>
        <button
          type="button"
          onClick={onClose}
          className="text-gray-500 hover:text-white transition"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="space-y-3 text-xs">
        <label className="block text-[10px] text-gray-500 uppercase font-bold mb-1">
          {actionType === 'MIN_LEVEL' ? 'Novo Mínimo de Alerta' : 'Quantidade'}
          <input
            type="number"
            step="any"
            placeholder="Ex: 5"
            value={actionValue}
            onChange={(e) => onChangeValue(e.target.value)}
            className="w-full mt-1 rounded border border-gray-855 bg-gray-950 px-3 py-2 text-white placeholder-gray-650 focus:border-brand-500 focus:outline-none"
          />
        </label>

        {actionType !== 'MIN_LEVEL' && (
          <label className="block text-[10px] text-gray-500 uppercase font-bold mb-1">
            Motivo
            <input
              type="text"
              placeholder="Ex: Recebimento de carga"
              value={actionReason}
              onChange={(e) => onChangeReason(e.target.value)}
              className="w-full mt-1 rounded border border-gray-855 bg-gray-950 px-3 py-2 text-white placeholder-gray-655 focus:border-brand-500 focus:outline-none"
            />
          </label>
        )}

        <button
          type="button"
          onClick={onSubmit}
          className="flex w-full items-center justify-center gap-1.5 rounded-lg bg-brand-500 hover:bg-brand-600 active:scale-[0.98] py-2 text-xs font-bold text-white transition duration-200"
        >
          Confirmar
        </button>
      </div>
    </div>
  )
}

interface CreateStockItemModalProps {
  onClose: () => void
  onSubmit: (data: {
    name: string
    category: string
    quantity: number
    unit: string
    minLevel: number
  }) => void
}

function CreateStockItemModal({ onClose, onSubmit }: CreateStockItemModalProps) {
  const [name, setName] = useState('')
  const [category, setCategory] = useState('RAW_MATERIAL')
  const [quantity, setQuantity] = useState('0')
  const [unit, setUnit] = useState('un')
  const [minLevel, setMinLevel] = useState('0')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return
    onSubmit({
      name,
      category,
      quantity: Number(quantity),
      unit,
      minLevel: Number(minLevel),
    })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-955/80 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-2xl border border-gray-800 bg-gray-900 p-6 shadow-xl space-y-4">
        <div className="flex items-center justify-between border-b border-gray-800 pb-3">
          <h3 className="text-base font-bold text-gray-100">Adicionar Novo Insumo</h3>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-500 hover:text-white transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3.5 text-xs">
          <label className="block text-[10px] uppercase font-bold text-gray-500">
            Nome
            <input
              type="text"
              required
              placeholder="Ex: Pão de Hambúrguer"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full mt-1 rounded border border-gray-805 bg-gray-955 px-3 py-2 text-white focus:border-brand-500 focus:outline-none"
            />
          </label>

          <div className="grid grid-cols-2 gap-3">
            <label className="block text-[10px] uppercase font-bold text-gray-500">
              Categoria
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full mt-1 rounded border border-gray-805 bg-gray-955 px-3 py-2 text-white focus:border-brand-500 focus:outline-none"
              >
                <option value="RAW_MATERIAL">Insumo Base</option>
                <option value="BEVERAGE">Bebida</option>
                <option value="PACKAGING">Embalagem</option>
              </select>
            </label>

            <label className="block text-[10px] uppercase font-bold text-gray-500">
              Unidade
              <select
                value={unit}
                onChange={(e) => setUnit(e.target.value)}
                className="w-full mt-1 rounded border border-gray-805 bg-gray-955 px-3 py-2 text-white focus:border-brand-500 focus:outline-none"
              >
                <option value="un">Unidade (un)</option>
                <option value="kg">Quilograma (kg)</option>
                <option value="g">Grama (g)</option>
                <option value="l">Litro (l)</option>
                <option value="ml">Mililitro (ml)</option>
              </select>
            </label>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <label className="block text-[10px] uppercase font-bold text-gray-500">
              Qtd. Inicial
              <input
                type="number"
                step="any"
                required
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                className="w-full mt-1 rounded border border-gray-805 bg-gray-955 px-3 py-2 text-white focus:border-brand-500 focus:outline-none"
              />
            </label>

            <label className="block text-[10px] uppercase font-bold text-gray-500">
              Alerta Mínimo
              <input
                type="number"
                step="any"
                required
                value={minLevel}
                onChange={(e) => setMinLevel(e.target.value)}
                className="w-full mt-1 rounded border border-gray-805 bg-gray-955 px-3 py-2 text-white focus:border-brand-500 focus:outline-none"
              />
            </label>
          </div>

          <button
            type="submit"
            className="w-full rounded-lg bg-brand-500 hover:bg-brand-600 active:scale-[0.98] py-2.5 text-xs font-bold text-white transition duration-200 mt-2"
          >
            Salvar Insumo
          </button>
        </form>
      </div>
    </div>
  )
}

async function submitStockAction(
  itemId: number,
  type: 'ADD' | 'DEDUCT' | 'ADJUST' | 'MIN_LEVEL',
  value: number,
  reason: string,
) {
  if (type === 'ADD') {
    return httpClient.post(`/v1/stock/items/${itemId}/add`, { quantity: value, reason })
  }
  if (type === 'DEDUCT') {
    return httpClient.post(`/v1/stock/items/${itemId}/deduct`, { quantity: value, reason })
  }
  if (type === 'ADJUST') {
    return httpClient.post(`/v1/stock/items/${itemId}/adjust`, { new_quantity: value, reason })
  }
  if (type === 'MIN_LEVEL') {
    return httpClient.put(`/v1/stock/items/${itemId}/min-level`, { min_stock_level: value })
  }
}

interface HistoryPanelProps {
  activeHistoryItem: StockItem | null
  isLoadingHistory: boolean
  historyMovements: StockMovement[]
}

function HistoryPanel({
  activeHistoryItem,
  isLoadingHistory,
  historyMovements,
}: HistoryPanelProps) {
  if (!activeHistoryItem) {
    return (
      <div className="py-12 text-center text-xs text-gray-500">
        Clique no ícone de histórico de um item para visualizar suas movimentações.
      </div>
    )
  }

  return (
    <div className="mt-4 space-y-4">
      <div className="text-xs font-bold text-gray-200">
        {activeHistoryItem.name}{' '}
        <span className="text-[10px] text-gray-500 font-mono">
          ({activeHistoryItem.current_quantity_unit})
        </span>
      </div>

      {isLoadingHistory ? (
        <div className="text-center py-8 text-xs text-gray-500 animate-pulse">
          Buscando registros...
        </div>
      ) : historyMovements.length === 0 ? (
        <div className="text-center py-8 text-xs text-gray-500">
          Nenhuma movimentação registrada para este item.
        </div>
      ) : (
        <div className="max-h-[300px] overflow-y-auto space-y-2 pr-1">
          {historyMovements.map((move) => {
            const isAdd = move.movement_type === 'ADD'
            const isDeduct = move.movement_type === 'DEDUCT'
            const time = new Date(move.created_at).toLocaleDateString()
            let typeColor = 'text-gray-400'
            let typeSign = ''

            if (isAdd) {
              typeColor = 'text-emerald-400'
              typeSign = '+'
            } else if (isDeduct) {
              typeColor = 'text-red-400'
              typeSign = '-'
            }

            return (
              <div
                key={move.id}
                className="rounded border border-gray-850 bg-gray-950/30 p-2.5 text-[11px] space-y-1"
              >
                <div className="flex justify-between">
                  <span className={`font-bold ${typeColor}`}>
                    {typeSign}
                    {move.quantity_changed}
                  </span>
                  <span className="text-[10px] text-gray-500">{time}</span>
                </div>
                <div className="text-gray-400 truncate">{move.reason}</div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default function StockManager() {
  const [stockItems, setStockItems] = useState<StockItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [showCreateModal, setShowCreateModal] = useState(false)
  const [activeHistoryItem, setActiveHistoryItem] = useState<StockItem | null>(null)
  const [historyMovements, setHistoryMovements] = useState<StockMovement[]>([])
  const [isLoadingHistory, setIsLoadingHistory] = useState(false)

  const [actionItemId, setActionItemId] = useState<number | null>(null)
  const [actionType, setActionType] = useState<'ADD' | 'DEDUCT' | 'ADJUST' | 'MIN_LEVEL' | null>(
    null,
  )
  const [actionValue, setActionValue] = useState('')
  const [actionReason, setActionReason] = useState('')

  const fetchStock = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const res = await httpClient.get<StockItem[]>('/v1/stock/items')
      setStockItems(res.data)
    } catch (_err) {
      setError('Erro ao carregar itens de estoque.')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchStock()
  }, [fetchStock])

  const handleCreateItemSubmit = async (data: {
    name: string
    category: string
    quantity: number
    unit: string
    minLevel: number
  }) => {
    try {
      const itemId = Date.now() + Math.floor(Math.random() * 1000)
      await httpClient.post('/v1/stock/items', {
        id: itemId,
        name: data.name,
        category: data.category,
        current_quantity: data.quantity,
        unit: data.unit,
        min_stock_level: data.minLevel,
      })
      setShowCreateModal(false)
      fetchStock()
    } catch (_err) {
      alert('Erro ao criar item no estoque. Tente novamente.')
    }
  }

  const handleOpenAction = (item: StockItem, type: 'ADD' | 'DEDUCT' | 'ADJUST' | 'MIN_LEVEL') => {
    setActionItemId(item.id)
    setActionType(type)
    setActionValue('')
    setActionReason(type === 'MIN_LEVEL' ? '' : 'Ajuste manual')
  }

  const handleCloseAction = () => {
    setActionItemId(null)
    setActionType(null)
    setActionValue('')
  }

  const handleSubmitAction = async () => {
    if (!actionItemId || !actionType || !actionValue) return
    const valueNum = Number(actionValue)
    if (Number.isNaN(valueNum)) return

    try {
      await submitStockAction(actionItemId, actionType, valueNum, actionReason || 'Operação manual')
      handleCloseAction()
      fetchStock()
    } catch (_err) {
      alert('Operação falhou. Verifique se a quantidade é válida.')
    }
  }

  const handleViewHistory = async (item: StockItem) => {
    setActiveHistoryItem(item)
    setIsLoadingHistory(true)
    try {
      const res = await httpClient.get<StockMovement[]>(`/v1/stock/items/${item.id}/movements`)
      setHistoryMovements(res.data)
    } catch (_err) {
      alert('Erro ao carregar histórico de movimentações.')
    } finally {
      setIsLoadingHistory(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-gray-800/80 pb-4">
        <div>
          <h2 className="text-xl font-bold text-gray-100 flex items-center gap-2">
            Controle de Estoque
          </h2>
          <p className="text-xs text-gray-400">
            Gerencie insumos, bebidas e níveis críticos de armazenamento
          </p>
        </div>

        <div className="flex gap-2">
          <button
            type="button"
            onClick={fetchStock}
            className="flex items-center gap-1.5 rounded-lg border border-gray-800 hover:border-gray-700 bg-gray-900/50 px-3.5 py-2 text-xs font-semibold text-gray-300 hover:text-white transition duration-200"
          >
            <RotateCcw className="h-4 w-4" />
            Atualizar
          </button>
          <button
            type="button"
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-1.5 rounded-lg bg-brand-500 hover:bg-brand-600 px-4 py-2 text-xs font-bold text-white transition duration-200 active:scale-[0.98]"
          >
            <PlusCircle className="h-4 w-4" />
            Novo Insumo
          </button>
        </div>
      </div>

      {isLoading && stockItems.length === 0 ? (
        <div className="text-center py-20 text-xs text-gray-500">Carregando inventário...</div>
      ) : error ? (
        <div className="rounded-xl border border-red-900/50 bg-red-950/20 p-6 text-center text-red-400">
          {error}
        </div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Main List */}
          <div className="lg:col-span-2 space-y-4">
            <StockTable
              items={stockItems}
              onOpenAction={handleOpenAction}
              onViewHistory={handleViewHistory}
            />
          </div>

          {/* Right Col: Action Form or History */}
          <div className="space-y-6">
            {actionItemId && actionType && (
              <StockActionCard
                actionType={actionType}
                actionValue={actionValue}
                actionReason={actionReason}
                onChangeValue={setActionValue}
                onChangeReason={setActionReason}
                onClose={handleCloseAction}
                onSubmit={handleSubmitAction}
              />
            )}

            {/* History Panel */}
            <div className="rounded-xl border border-gray-800/80 bg-gray-900/30 p-4 backdrop-blur-md">
              <h3 className="border-b border-gray-850 pb-2.5 text-xs font-bold uppercase tracking-wider text-gray-400 flex items-center gap-2">
                <FileSpreadsheet className="h-4 w-4 text-purple-400" />
                Histórico de Movimentações
              </h3>

              <HistoryPanel
                activeHistoryItem={activeHistoryItem}
                isLoadingHistory={isLoadingHistory}
                historyMovements={historyMovements}
              />
            </div>
          </div>
        </div>
      )}

      {/* Create Item Modal */}
      {showCreateModal && (
        <CreateStockItemModal
          onClose={() => setShowCreateModal(false)}
          onSubmit={handleCreateItemSubmit}
        />
      )}
    </div>
  )
}
