import {
  AlertTriangle,
  Edit2,
  FileSpreadsheet,
  History,
  Minus,
  Plus,
  PlusCircle,
  RotateCcw,
  Search,
  Sliders,
  Trash2,
  Utensils,
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
  movement_type:
    | 'ADD'
    | 'DEDUCT'
    | 'ADJUST'
    | 'MIN_LEVEL'
    | 'INPUT'
    | 'OUTPUT'
    | 'ADJUSTMENT'
    | 'PRODUCTION'
    | 'WASTE'
  quantity_changed: number
  reason: string
  created_at: string
}

interface StockItemRowProps {
  item: StockItem
  onOpenAction: (item: StockItem, type: 'ADD' | 'DEDUCT' | 'ADJUST') => void
  onViewHistory: (item: StockItem) => void
  onEdit: (item: StockItem) => void
  onDelete: (item: StockItem) => void
}

function StockItemRow({ item, onOpenAction, onViewHistory, onEdit, onDelete }: StockItemRowProps) {
  return (
    <tr
      className={`hover:bg-white/[0.02] transition-colors border-b border-gray-900/60 ${item.is_low_stock ? 'bg-rose-500/[0.02]' : ''}`}
    >
      <td className="px-5 py-4">
        <div className="font-bold text-gray-100 flex items-center gap-2 text-xs">
          {item.name}
          {item.is_low_stock && (
            <span
              className="rounded-lg bg-rose-500/10 border border-rose-500/25 px-2 py-0.5 text-[8px] font-black uppercase tracking-wider text-rose-400 flex items-center gap-1 shadow-inner"
              title="Estoque abaixo do mínimo!"
            >
              <AlertTriangle className="h-2.5 w-2.5 animate-pulse" />
              Crítico
            </span>
          )}
        </div>
        <span className="text-[9px] text-gray-500 font-mono">ID: #{item.id}</span>
      </td>
      <td className="px-5 py-4">
        <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-gray-900/40 text-gray-400 border border-gray-850">
          {item.category === 'RAW_MATERIAL'
            ? 'Insumo Base'
            : item.category === 'SUPPLEMENT'
              ? 'Suplemento'
              : item.category === 'BEVERAGE'
                ? 'Bebida'
                : item.category === 'PACKAGING'
                  ? 'Embalagem'
                  : 'Outros'}
        </span>
      </td>
      <td className="px-5 py-4 font-mono font-bold text-xs text-gray-200">
        {item.current_quantity_amount}{' '}
        <span className="text-[10px] text-gray-500 font-sans font-medium">
          {item.current_quantity_unit}
        </span>
      </td>
      <td className="px-5 py-4 font-mono text-xs text-gray-400">
        {item.min_stock_level}{' '}
        <span className="text-[10px] text-gray-500 font-sans font-medium">
          {item.current_quantity_unit}
        </span>
      </td>
      <td className="px-5 py-4 text-right space-x-1 whitespace-nowrap">
        <button
          type="button"
          onClick={() => onOpenAction(item, 'ADD')}
          className="p-2 rounded-lg bg-gray-900/40 border border-gray-850 hover:border-emerald-500/30 hover:text-emerald-400 text-gray-400 transition"
          title="Entrada (+)"
        >
          <Plus className="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          onClick={() => onOpenAction(item, 'DEDUCT')}
          className="p-2 rounded-lg bg-gray-900/40 border border-gray-850 hover:border-red-500/30 hover:text-red-400 text-gray-400 transition"
          title="Saída (-)"
        >
          <Minus className="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          onClick={() => onOpenAction(item, 'ADJUST')}
          className="p-2 rounded-lg bg-gray-900/40 border border-gray-850 hover:border-blue-500/30 hover:text-blue-400 text-gray-400 transition"
          title="Ajustar Inventário"
        >
          <Sliders className="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          onClick={() => onEdit(item)}
          className="p-2 rounded-lg bg-gray-900/40 border border-gray-850 hover:border-blue-500/30 hover:text-blue-400 text-gray-400 transition"
          title="Editar Insumo"
        >
          <Edit2 className="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          onClick={() => onDelete(item)}
          className="p-2 rounded-lg bg-gray-900/40 border border-gray-850 hover:border-red-500/30 hover:text-red-400 text-gray-400 transition"
          title="Excluir Insumo"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          onClick={() => onViewHistory(item)}
          className="p-2 rounded-lg bg-gray-900/40 border border-gray-850 hover:border-purple-500/30 hover:text-purple-400 text-gray-400 transition"
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
  onOpenAction: (item: StockItem, type: 'ADD' | 'DEDUCT' | 'ADJUST') => void
  onViewHistory: (item: StockItem) => void
  onEdit: (item: StockItem) => void
  onDelete: (item: StockItem) => void
}

function StockTable({ items, onOpenAction, onViewHistory, onEdit, onDelete }: StockTableProps) {
  return (
    <div className="rounded-2xl border border-gray-900 bg-gray-950/10 overflow-hidden backdrop-blur-md glass-card">
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-left text-xs text-gray-300">
          <thead className="bg-gray-950/40 text-gray-450 border-b border-gray-900/60 uppercase tracking-widest text-[9px] font-extrabold">
            <tr>
              <th className="px-5 py-4">Insumo / Descrição</th>
              <th className="px-5 py-4">Categoria</th>
              <th className="px-5 py-4">Qtd. Atual</th>
              <th className="px-5 py-4">Limite Alerta</th>
              <th className="px-5 py-4 text-right">Painel de Ações</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-900/40">
            {items.length === 0 ? (
              <tr>
                <td
                  colSpan={5}
                  className="px-5 py-12 text-center text-gray-500 text-xs font-semibold"
                >
                  Nenhum insumo encontrado com os filtros atuais.
                </td>
              </tr>
            ) : (
              items.map((item) => (
                <StockItemRow
                  key={item.id}
                  item={item}
                  onOpenAction={onOpenAction}
                  onViewHistory={onViewHistory}
                  onEdit={onEdit}
                  onDelete={onDelete}
                />
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

interface StockActionCardProps {
  activeItem: StockItem
  actionType: 'ADD' | 'DEDUCT' | 'ADJUST'
  actionValue: string
  actionCost: string
  actionReason: string
  adjustTransactionType: string
  onChangeValue: (val: string) => void
  onChangeCost: (val: string) => void
  onChangeReason: (val: string) => void
  onChangeAdjustType: (val: string) => void
  onClose: () => void
  onSubmit: () => void
  isSubmitting: boolean
}

function StockActionCard({
  activeItem,
  actionType,
  actionValue,
  actionCost,
  actionReason,
  adjustTransactionType,
  onChangeValue,
  onChangeCost,
  onChangeReason,
  onChangeAdjustType,
  onClose,
  onSubmit,
  isSubmitting,
}: StockActionCardProps) {
  return (
    <div className="rounded-2xl border border-brand-500/20 bg-brand-500/5 p-5 backdrop-blur-md space-y-4">
      <div className="flex items-center justify-between border-b border-gray-900/60 pb-2.5">
        <div>
          <h3 className="text-xs font-black uppercase tracking-wider text-brand-400">
            {actionType === 'ADD'
              ? 'Registrar Entrada'
              : actionType === 'DEDUCT'
                ? 'Registrar Retirada'
                : 'Ajustar Inventário'}
          </h3>
          <span className="text-[10px] text-gray-400 font-bold mt-0.5">{activeItem.name}</span>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="text-gray-500 hover:text-white transition rounded-lg p-1 hover:bg-white/[0.03]"
        >
          <X className="h-4.5 w-4.5" />
        </button>
      </div>

      <div className="space-y-4 text-xs">
        {/* Transaction type selector — only for ADJUST */}
        {actionType === 'ADJUST' && (
          <div className="space-y-1.5">
            <span className="block text-[10px] text-gray-500 uppercase font-extrabold">
              Tipo de Lançamento
            </span>
            <select
              value={adjustTransactionType}
              onChange={(e) => onChangeAdjustType(e.target.value)}
              className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input bg-[#0c0c12]"
            >
              <option value="ADJUSTMENT">📋 Ajuste de Inventário (contagem física)</option>
              <option value="WASTE">🗑️ Perda / Desperdício</option>
              <option value="PRODUCTION">🏭 Produção Interna (item fabricado)</option>
            </select>
          </div>
        )}

        <div className="space-y-1.5">
          <span className="block text-[10px] text-gray-500 uppercase font-extrabold">
            Quantidade
          </span>
          <div className="relative">
            <input
              type="number"
              step="any"
              placeholder="Digite a quantidade..."
              value={actionValue}
              onChange={(e) => onChangeValue(e.target.value)}
              className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input"
            />
            <span className="absolute right-4 top-1/2 -translate-y-1/2 text-xs font-bold text-gray-500 font-mono">
              {activeItem.current_quantity_unit}
            </span>
          </div>
        </div>

        {actionType === 'ADD' && (
          <div className="space-y-1.5">
            <span className="block text-[10px] text-gray-500 uppercase font-extrabold">
              Custo Unitário (R$)
            </span>
            <div className="relative">
              <input
                type="number"
                step="any"
                min="0.01"
                required
                placeholder="Ex: 25.90"
                value={actionCost}
                onChange={(e) => onChangeCost(e.target.value)}
                className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input"
              />
              <span className="absolute right-4 top-1/2 -translate-y-1/2 text-xs font-bold text-gray-500 font-mono">
                R$
              </span>
            </div>
          </div>
        )}

        <div className="space-y-1.5">
          <span className="block text-[10px] text-gray-500 uppercase font-extrabold">
            Justificativa
          </span>
          <input
            type="text"
            placeholder={
              actionType === 'ADJUST' && adjustTransactionType === 'WASTE'
                ? 'Ex: Produto vencido, queda acidental...'
                : actionType === 'ADJUST' && adjustTransactionType === 'PRODUCTION'
                  ? 'Ex: Lote produzido em 08/06/2026'
                  : 'Ex: Reposição semanal de carga'
            }
            value={actionReason}
            onChange={(e) => onChangeReason(e.target.value)}
            className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input"
          />
        </div>

        <button
          type="button"
          onClick={onSubmit}
          disabled={isSubmitting}
          className="flex w-full items-center justify-center gap-1.5 rounded-xl bg-brand-500 hover:bg-brand-600 disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98] py-3 text-xs font-bold text-white transition duration-200 shadow-lg shadow-brand-500/10 animate-pulse-glow"
        >
          {isSubmitting ? 'Processando...' : 'Confirmar Lançamento'}
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
    costAmount: number
  }) => void
}

function CreateStockItemModal({ onClose, onSubmit }: CreateStockItemModalProps) {
  const [name, setName] = useState('')
  const [category, setCategory] = useState('RAW_MATERIAL')
  const [quantity, setQuantity] = useState('0')
  const [unit, setUnit] = useState('un')
  const [minLevel, setMinLevel] = useState('0')
  const [costAmount, setCostAmount] = useState('0')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return
    onSubmit({
      name,
      category,
      quantity: Number(quantity),
      unit,
      minLevel: Number(minLevel),
      costAmount: Number(costAmount) || 0,
    })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-md rounded-2xl border border-gray-900 bg-[#0c0c12] p-6 space-y-6 shadow-2xl glass-card">
        <div className="flex items-center justify-between border-b border-gray-900/60 pb-3">
          <h2 className="text-sm font-black text-white uppercase tracking-wider">
            Novo Insumo de Estoque
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-500 hover:text-white transition rounded-lg p-1 hover:bg-white/[0.03]"
          >
            <X className="h-4.5 w-4.5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          <div className="space-y-1.5">
            <span className="block text-[10px] text-gray-500 uppercase font-extrabold">
              Nome do Insumo
            </span>
            <input
              type="text"
              required
              placeholder="Ex: Queijo Coalho"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <span className="block text-[10px] text-gray-500 uppercase font-extrabold">
                Categoria
              </span>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input bg-[#0c0c12]"
              >
                <option value="RAW_MATERIAL">Insumo Base</option>
                <option value="SUPPLEMENT">Suplemento</option>
                <option value="BEVERAGE">Bebida</option>
                <option value="PACKAGING">Embalagem</option>
                <option value="OTHER">Outros</option>
              </select>
            </div>

            <div className="space-y-1.5">
              <span className="block text-[10px] text-gray-500 uppercase font-extrabold">
                Unidade de Medida
              </span>
              <select
                value={unit}
                onChange={(e) => setUnit(e.target.value)}
                className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input bg-[#0c0c12]"
              >
                <option value="un">Unidade (un)</option>
                <option value="g">Grama (g)</option>
                <option value="kg">Quilograma (kg)</option>
                <option value="ml">Mililitro (ml)</option>
                <option value="l">Litro (l)</option>
                <option value="oz">Onça (oz)</option>
                <option value="lb">Libra (lb)</option>
                <option value="fl_oz">Onça Líquida (fl_oz)</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-1.5">
              <span className="block text-[10px] text-gray-500 uppercase font-extrabold">
                Qtd. Inicial
              </span>
              <input
                type="number"
                step="any"
                required
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input"
              />
            </div>

            <div className="space-y-1.5">
              <span className="block text-[10px] text-gray-500 uppercase font-extrabold">
                Custo Unit. (R$)
              </span>
              <input
                type="number"
                step="any"
                min="0"
                placeholder="0,00"
                value={costAmount}
                onChange={(e) => setCostAmount(e.target.value)}
                className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input"
              />
            </div>

            <div className="space-y-1.5">
              <span className="block text-[10px] text-gray-500 uppercase font-extrabold">
                Mínimo Alerta
              </span>
              <input
                type="number"
                step="any"
                required
                value={minLevel}
                onChange={(e) => setMinLevel(e.target.value)}
                className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input"
              />
            </div>
          </div>

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 rounded-xl border border-gray-850 hover:border-gray-700 bg-gray-900/30 py-3 text-xs font-bold text-gray-300 hover:text-white transition"
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="flex-1 rounded-xl bg-brand-500 hover:bg-brand-600 active:scale-[0.98] py-3 text-xs font-bold text-white transition shadow-lg shadow-brand-500/10"
            >
              Salvar Insumo
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

interface EditStockItemModalProps {
  item: StockItem
  onClose: () => void
  onSubmit: (data: { name: string; category: string; unit: string; minLevel: number }) => void
}

function EditStockItemModal({ item, onClose, onSubmit }: EditStockItemModalProps) {
  const [name, setName] = useState(item.name)
  const [category, setCategory] = useState(item.category)
  const [unit, setUnit] = useState(item.current_quantity_unit)
  const [minLevel, setMinLevel] = useState(item.min_stock_level.toString())

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return
    onSubmit({
      name,
      category,
      unit,
      minLevel: Number(minLevel),
    })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-md rounded-2xl border border-gray-900 bg-[#0c0c12] p-6 space-y-6 shadow-2xl glass-card">
        <div className="flex items-center justify-between border-b border-gray-900/60 pb-3">
          <h2 className="text-sm font-black text-white uppercase tracking-wider">Editar Insumo</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-550 hover:text-white transition rounded-lg p-1 hover:bg-white/[0.03]"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          <div className="space-y-1.5">
            <span className="block text-[10px] text-gray-500 uppercase font-extrabold">
              Nome do Insumo
            </span>
            <input
              type="text"
              required
              placeholder="Ex: Queijo Coalho"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <span className="block text-[10px] text-gray-500 uppercase font-extrabold">
                Categoria
              </span>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input bg-[#0c0c12]"
              >
                <option value="RAW_MATERIAL">Insumo Base</option>
                <option value="SUPPLEMENT">Suplemento</option>
                <option value="BEVERAGE">Bebida</option>
                <option value="PACKAGING">Embalagem</option>
                <option value="OTHER">Outros</option>
              </select>
            </div>

            <div className="space-y-1.5">
              <span className="block text-[10px] text-gray-500 uppercase font-extrabold">
                Unidade de Medida
              </span>
              <select
                value={unit}
                onChange={(e) => setUnit(e.target.value)}
                className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input bg-[#0c0c12]"
              >
                <option value="un">Unidade (un)</option>
                <option value="g">Grama (g)</option>
                <option value="kg">Quilograma (kg)</option>
                <option value="ml">Mililitro (ml)</option>
                <option value="l">Litro (l)</option>
                <option value="oz">Onça (oz)</option>
                <option value="lb">Libra (lb)</option>
                <option value="fl_oz">Onça Líquida (fl_oz)</option>
              </select>
            </div>
          </div>

          <div className="space-y-1.5">
            <span className="block text-[10px] text-gray-500 uppercase font-extrabold">
              Mínimo Alerta (Estoque Mínimo)
            </span>
            <input
              type="number"
              step="any"
              required
              value={minLevel}
              onChange={(e) => setMinLevel(e.target.value)}
              className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input"
            />
          </div>

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 rounded-xl border border-gray-850 hover:border-gray-700 bg-gray-900/30 py-3 text-xs font-bold text-gray-300 hover:text-white transition"
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="flex-1 rounded-xl bg-brand-500 hover:bg-brand-600 active:scale-[0.98] py-3 text-xs font-bold text-white transition shadow-lg shadow-brand-500/10"
            >
              Salvar Alterações
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function submitStockAction(
  itemId: number,
  type: 'ADD' | 'DEDUCT' | 'ADJUST',
  value: number,
  reason: string,
  costAmount?: number,
  adjustTransactionType = 'ADJUSTMENT',
) {
  if (type === 'ADD') {
    return httpClient.post(`/v1/stock/items/${itemId}/add`, {
      quantity: value,
      cost_amount: costAmount ?? 0,
      reason,
    })
  }
  if (type === 'DEDUCT') {
    return httpClient.post(`/v1/stock/items/${itemId}/deduct`, { quantity: value, reason })
  }
  if (type === 'ADJUST') {
    return httpClient.post(`/v1/stock/items/${itemId}/adjust`, {
      new_quantity: value,
      reason,
      transaction_type: adjustTransactionType,
    })
  }
}

interface ConsumedByItem {
  menu_item_id: number
  menu_item_name: string
  quantity_value: number
  quantity_unit: string
}

interface HistoryPanelProps {
  activeHistoryItem: StockItem | null
  isLoadingHistory: boolean
  historyMovements: StockMovement[]
  consumedBy: ConsumedByItem[]
  isLoadingConsumedBy: boolean
}

function HistoryPanel({
  activeHistoryItem,
  isLoadingHistory,
  historyMovements,
  consumedBy,
  isLoadingConsumedBy,
}: HistoryPanelProps) {
  if (!activeHistoryItem) {
    return (
      <div className="py-16 text-center text-xs text-gray-550 font-medium">
        Selecione o histórico de um insumo para visualizar as movimentações registradas.
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="text-xs font-bold text-gray-200 flex items-center justify-between">
        <span>{activeHistoryItem.name}</span>
        <span className="text-[10px] text-brand-400 bg-brand-500/10 border border-brand-500/20 px-2 py-0.5 rounded font-mono uppercase font-black">
          {activeHistoryItem.current_quantity_unit}
        </span>
      </div>

      {isLoadingHistory ? (
        <div className="text-center py-12 text-xs text-gray-500 animate-pulse">
          Buscando registros na rede...
        </div>
      ) : historyMovements.length === 0 ? (
        <div className="text-center py-12 text-xs text-gray-500 font-semibold">
          Nenhuma movimentação para este insumo.
        </div>
      ) : (
        <div className="max-h-[350px] overflow-y-auto space-y-2 pr-1">
          {historyMovements.map((move) => {
            const isAdd = move.movement_type === 'ADD' || move.movement_type === 'INPUT'
            const isDeduct =
              move.movement_type === 'DEDUCT' ||
              move.movement_type === 'OUTPUT' ||
              move.movement_type === 'WASTE'
            const isMin = move.movement_type === 'MIN_LEVEL'
            const time = new Date(move.created_at).toLocaleDateString()
            let typeColor = 'text-gray-400 border-gray-900 bg-gray-900/20'
            let typeSign = ''
            let typeLabel = 'Ajuste'

            if (isAdd) {
              typeColor = 'text-emerald-450 border-emerald-500/10 bg-emerald-500/[0.03]'
              typeSign = '+'
              typeLabel = 'Entrada'
            } else if (isDeduct) {
              typeColor = 'text-rose-450 border-rose-500/10 bg-rose-500/[0.03]'
              typeSign = '-'
              typeLabel = 'Saída'
            } else if (isMin) {
              typeColor = 'text-amber-450 border-amber-500/10 bg-amber-500/[0.03]'
              typeLabel = 'Limiar'
            }

            return (
              <div
                key={move.id}
                className={`rounded-xl border p-3 text-[11px] space-y-1.5 ${typeColor}`}
              >
                <div className="flex justify-between items-center font-bold">
                  <span className="uppercase tracking-wider text-[9px]">{typeLabel}</span>
                  <span className="text-[10px] text-gray-500 font-medium">{time}</span>
                </div>
                <div className="flex justify-between items-baseline pt-1">
                  <span className="text-xs font-black">
                    {typeSign}
                    {move.quantity_changed}
                  </span>
                  <span className="text-[10px] text-gray-400 truncate max-w-[150px] font-medium">
                    {move.reason}
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Consumed-By Section */}
      {activeHistoryItem && (
        <div className="border-t border-gray-900/40 pt-4 mt-4">
          <h4 className="text-[10px] font-extrabold uppercase tracking-widest text-gray-500 flex items-center gap-2 mb-3">
            <Utensils className="h-3.5 w-3.5 text-emerald-400" />
            Consumido por ({consumedBy.length} receitas)
          </h4>
          {isLoadingConsumedBy ? (
            <div className="text-center py-4 text-[10px] text-gray-500 animate-pulse">
              Carregando...
            </div>
          ) : consumedBy.length === 0 ? (
            <div className="text-center py-4 text-[10px] text-gray-600 italic">
              Nenhuma receita consome este insumo.
            </div>
          ) : (
            <div className="space-y-2">
              {consumedBy.map((cb) => (
                <div
                  key={cb.menu_item_id}
                  className="flex items-center justify-between rounded-xl border border-gray-900/60 bg-gray-950/20 p-3"
                >
                  <span className="text-xs font-bold text-gray-200">{cb.menu_item_name}</span>
                  <span className="text-[10px] text-gray-400 font-mono">
                    {cb.quantity_value} {cb.quantity_unit} por porção
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function getTabStyles(isActive: boolean): string {
  if (isActive) {
    return 'border-brand-500 text-brand-400 font-extrabold bg-brand-500/5'
  }
  return 'border-transparent text-gray-450 hover:text-gray-200 hover:bg-gray-900/10'
}

function getTabCounterStyles(isActive: boolean): string {
  if (isActive) {
    return 'bg-brand-500/20 text-brand-300'
  }
  return 'bg-gray-900 text-gray-500'
}

export default function StockManager() {
  const [stockItems, setStockItems] = useState<StockItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterTab, setFilterTab] = useState<
    'ALL' | 'RAW_MATERIAL' | 'BEVERAGE' | 'PACKAGING' | 'SUPPLEMENT' | 'OTHER'
  >('ALL')
  const [showOnlyLowStock, setShowOnlyLowStock] = useState(false)

  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [editingItem, setEditingItem] = useState<StockItem | null>(null)
  const [activeHistoryItem, setActiveHistoryItem] = useState<StockItem | null>(null)
  const [historyMovements, setHistoryMovements] = useState<StockMovement[]>([])
  const [isLoadingHistory, setIsLoadingHistory] = useState(false)
  const [consumedBy, setConsumedBy] = useState<ConsumedByItem[]>([])
  const [isLoadingConsumedBy, setIsLoadingConsumedBy] = useState(false)

  const [actionItemId, setActionItemId] = useState<number | null>(null)
  const [actionType, setActionType] = useState<'ADD' | 'DEDUCT' | 'ADJUST' | null>(null)
  const [actionValue, setActionValue] = useState('')
  const [actionCost, setActionCost] = useState('')
  const [actionReason, setActionReason] = useState('')
  const [adjustTransactionType, setAdjustTransactionType] = useState('ADJUSTMENT')
  const [isSubmittingAction, setIsSubmittingAction] = useState(false)

  const fetchStock = useCallback(async () => {
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
    setIsLoading(true)
    fetchStock()
  }, [fetchStock])

  const handleCreateItemSubmit = async (data: {
    name: string
    category: string
    quantity: number
    unit: string
    minLevel: number
    costAmount: number
  }) => {
    try {
      await httpClient.post('/v1/stock/items', {
        name: data.name,
        category: data.category,
        current_quantity: data.quantity,
        initial_cost_amount: data.costAmount,
        unit: data.unit,
        min_stock_level: data.minLevel,
      })
      setShowCreateModal(false)
      fetchStock()
    } catch (_err) {
      alert('Erro ao criar item no estoque. Tente novamente.')
    }
  }

  const handleEditItemClick = (item: StockItem) => {
    setEditingItem(item)
    setShowEditModal(true)
  }

  const handleEditItemSubmit = async (data: {
    name: string
    category: string
    unit: string
    minLevel: number
  }) => {
    if (!editingItem) return
    try {
      await httpClient.put(`/v1/stock/items/${editingItem.id}`, {
        name: data.name,
        category: data.category,
        unit: data.unit,
        min_stock_level: data.minLevel,
      })
      setShowEditModal(false)
      setEditingItem(null)
      fetchStock()
    } catch (_err) {
      alert('Erro ao atualizar item de estoque. Tente novamente.')
    }
  }

  const handleDeleteItem = async (item: StockItem) => {
    const confirmed = window.confirm(`Deseja realmente remover o insumo "${item.name}"?`)
    if (!confirmed) return
    try {
      await httpClient.delete(`/v1/stock/items/${item.id}`)
      fetchStock()
      if (activeHistoryItem?.id === item.id) {
        setActiveHistoryItem(null)
      }
    } catch (_err) {
      alert('Erro ao excluir item de estoque. Verifique se ele está associado a alguma receita.')
    }
  }

  const handleOpenAction = (item: StockItem, type: 'ADD' | 'DEDUCT' | 'ADJUST') => {
    setActionItemId(item.id)
    setActionType(type)
    setActionValue('')
    setActionCost('')
    setActionReason('Ajuste manual')
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
    if (isSubmittingAction) return

    setIsSubmittingAction(true)
    try {
      await submitStockAction(
        actionItemId,
        actionType,
        valueNum,
        actionReason || 'Operação manual',
        actionType === 'ADD' ? Number(actionCost) || 0 : undefined,
        adjustTransactionType,
      )
      handleCloseAction()
      fetchStock()
    } catch (_err) {
      alert('Operação falhou. Verifique se a quantidade é válida.')
    } finally {
      setIsSubmittingAction(false)
    }
  }

  const handleViewHistory = async (item: StockItem) => {
    setActiveHistoryItem(item)
    setIsLoadingHistory(true)
    setIsLoadingConsumedBy(true)
    try {
      const [movRes, consumedRes] = await Promise.all([
        httpClient.get<StockMovement[]>(`/v1/stock/items/${item.id}/movements`),
        httpClient.get<ConsumedByItem[]>(`/v1/stock/items/${item.id}/consumed-by`),
      ])
      setHistoryMovements(movRes.data)
      setConsumedBy(consumedRes.data)
    } catch (_err) {
      alert('Erro ao carregar dados do insumo.')
    } finally {
      setIsLoadingHistory(false)
      setIsLoadingConsumedBy(false)
    }
  }

  const getActiveItem = (): StockItem | undefined => {
    return stockItems.find((item) => item.id === actionItemId)
  }

  // Filter items based on search query, category tab, and low stock toggle
  const filteredItems = stockItems.filter((item) => {
    const matchesSearch = item.name.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesTab = filterTab === 'ALL' || item.category === filterTab
    const matchesLowStock = !showOnlyLowStock || item.is_low_stock
    return matchesSearch && matchesTab && matchesLowStock
  })

  const lowStockCount = stockItems.filter((item) => item.is_low_stock).length
  const activeItem = getActiveItem()

  const tabs: {
    id: 'ALL' | 'RAW_MATERIAL' | 'BEVERAGE' | 'PACKAGING' | 'SUPPLEMENT' | 'OTHER'
    label: string
    count: number
  }[] = [
    { id: 'ALL', label: 'Todos', count: stockItems.length },
    {
      id: 'RAW_MATERIAL',
      label: 'Insumos Base',
      count: stockItems.filter((i) => i.category === 'RAW_MATERIAL').length,
    },
    {
      id: 'BEVERAGE',
      label: 'Bebidas',
      count: stockItems.filter((i) => i.category === 'BEVERAGE').length,
    },
    {
      id: 'PACKAGING',
      label: 'Embalagens',
      count: stockItems.filter((i) => i.category === 'PACKAGING').length,
    },
    {
      id: 'SUPPLEMENT',
      label: 'Suplementos',
      count: stockItems.filter((i) => i.category === 'SUPPLEMENT').length,
    },
    {
      id: 'OTHER',
      label: 'Outros',
      count: stockItems.filter((i) => i.category === 'OTHER').length,
    },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-gray-900/60 pb-4">
        <div>
          <h2 className="text-lg font-black text-white tracking-wide uppercase">
            Controle de Estoque
          </h2>
          <p className="text-xs text-gray-550 font-medium mt-0.5">
            Gerencie insumos, bebidas e níveis críticos de armazenamento
          </p>
        </div>

        <div className="flex gap-2">
          <button
            type="button"
            onClick={fetchStock}
            className="flex items-center gap-1.5 rounded-xl border border-gray-850 hover:border-gray-700 bg-gray-900/30 px-4 py-2.5 text-xs font-bold text-gray-300 hover:text-white transition duration-200"
          >
            <RotateCcw className="h-4 w-4" />
            Atualizar
          </button>
          <button
            type="button"
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-1.5 rounded-xl bg-brand-500 hover:bg-brand-600 px-4 py-2.5 text-xs font-bold text-white transition duration-200 active:scale-[0.98] shadow-lg shadow-brand-500/10"
          >
            <PlusCircle className="h-4 w-4" />
            Novo Insumo
          </button>
        </div>
      </div>

      {isLoading && stockItems.length === 0 ? (
        <div className="text-center py-20 text-xs text-gray-400 font-medium">
          Carregando inventário...
        </div>
      ) : error ? (
        <div className="rounded-2xl border border-red-955 bg-red-950/20 p-6 text-center text-red-400 font-bold text-xs">
          {error}
        </div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Main List Column */}
          <div className="lg:col-span-2 space-y-4">
            {/* Tabs Navigation */}
            <div className="flex border-b border-gray-900/60 overflow-x-auto no-scrollbar whitespace-nowrap scroll-smooth">
              {tabs.map((tab) => {
                const isActive = filterTab === tab.id
                return (
                  <button
                    type="button"
                    key={tab.id}
                    onClick={() => setFilterTab(tab.id)}
                    className={`flex items-center gap-1.5 px-4 py-3 text-xs font-bold transition-all duration-300 border-b-2 whitespace-nowrap cursor-pointer select-none ${getTabStyles(
                      isActive,
                    )}`}
                  >
                    {tab.label}
                    <span
                      className={`text-[9px] px-1.5 py-0.5 rounded-full font-mono font-bold ${getTabCounterStyles(
                        isActive,
                      )}`}
                    >
                      {tab.count}
                    </span>
                  </button>
                )
              })}
            </div>

            {/* Search toolbar */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 bg-gray-950/20 border border-gray-900 rounded-2xl p-4 glass-card">
              <div className="flex flex-wrap items-center gap-2.5">
                <span className="text-xs font-bold text-gray-400">
                  Visualizando {filteredItems.length} de {stockItems.length} itens
                </span>
                {lowStockCount > 0 && (
                  <button
                    type="button"
                    onClick={() => setShowOnlyLowStock(!showOnlyLowStock)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-[10px] font-black uppercase tracking-wider transition cursor-pointer select-none border ${
                      showOnlyLowStock
                        ? 'bg-rose-600 border-rose-600 text-white shadow-md shadow-rose-600/10'
                        : 'bg-rose-500/5 border-rose-500/20 text-rose-400 hover:bg-rose-500/10'
                    }`}
                  >
                    <span
                      className={`h-1.5 w-1.5 rounded-full bg-current ${
                        !showOnlyLowStock ? 'animate-pulse' : ''
                      }`}
                    />
                    Apenas Críticos ({lowStockCount})
                  </button>
                )}
              </div>
              <div className="relative w-full sm:w-64">
                <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
                <input
                  type="text"
                  placeholder="Pesquisar insumo..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-9.5 pr-4 py-2.5 text-xs text-white glass-input"
                />
              </div>
            </div>

            <StockTable
              items={filteredItems}
              onOpenAction={handleOpenAction}
              onViewHistory={handleViewHistory}
              onEdit={handleEditItemClick}
              onDelete={handleDeleteItem}
            />
          </div>

          {/* Right Column: Action Form or History Panel */}
          <div className="space-y-6">
            {actionItemId && actionType && activeItem && (
              <StockActionCard
                activeItem={activeItem}
                actionType={actionType}
                actionValue={actionValue}
                actionCost={actionCost}
                actionReason={actionReason}
                adjustTransactionType={adjustTransactionType}
                onChangeValue={setActionValue}
                onChangeCost={setActionCost}
                onChangeReason={setActionReason}
                onChangeAdjustType={setAdjustTransactionType}
                onClose={handleCloseAction}
                onSubmit={handleSubmitAction}
                isSubmitting={isSubmittingAction}
              />
            )}

            {/* History Panel */}
            <div className="rounded-2xl border border-gray-900 bg-gray-950/10 p-5 backdrop-blur-md glass-card">
              <h3 className="border-b border-gray-900/60 pb-3 text-xs font-black uppercase tracking-widest text-gray-500 flex items-center gap-2">
                <FileSpreadsheet className="h-4.5 w-4.5 text-purple-400" />
                Histórico de Movimentações
              </h3>

              <HistoryPanel
                activeHistoryItem={activeHistoryItem}
                isLoadingHistory={isLoadingHistory}
                historyMovements={historyMovements}
                consumedBy={consumedBy}
                isLoadingConsumedBy={isLoadingConsumedBy}
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

      {/* Edit Item Modal */}
      {showEditModal && editingItem && (
        <EditStockItemModal
          item={editingItem}
          onClose={() => {
            setShowEditModal(false)
            setEditingItem(null)
          }}
          onSubmit={handleEditItemSubmit}
        />
      )}
    </div>
  )
}
