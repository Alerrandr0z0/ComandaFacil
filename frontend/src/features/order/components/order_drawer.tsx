import { Ban, Check, DollarSign, Plus, Search, Send, Sparkles, X } from 'lucide-react'
import { useRef, useState } from 'react'
import type { MenuItem } from '@/features/menu/menu_hooks'
import type { DraftItem, OrderForm } from '../hooks/use_order_drawer'
import ModifierPicker from './modifier_picker'
import PaymentModal from './payment_modal'
import QuickSearch from './quick_search'

interface OrderDrawerProps {
  order: OrderForm | null
  draft: DraftItem[]
  activeMenu: { items: MenuItem[] } | null | undefined
  isLoading: boolean
  isSubmitting: boolean
  isRequestingPayment: boolean
  isProcessingPayment: boolean
  isCancelling: boolean
  isDelivering: boolean
  onClose: () => void
  onCreateOrder: (options?: {
    display_code?: string
    fulfillment_type: 'TABLE' | 'TAKEAWAY' | 'DELIVERY'
    table_number?: number | null
    customer_name?: string
    delivery_street?: string
    delivery_number?: string
    delivery_neighborhood?: string
    delivery_city?: string
    delivery_state?: string
    delivery_postal_code?: string
    delivery_estimated_time?: number
    delivery_tracking_code?: number
  }) => void
  onSelectItem: (item: MenuItem) => void
  onUpdateDraftQuantity: (itemId: number, delta: number) => void
  onUpdateDraftNotes: (itemId: number, notes: string) => void
  onSendToKitchen: () => Promise<unknown>
  onRequestPayment: () => Promise<unknown>
  onProcessPayment: (
    method: 'PIX' | 'CREDIT' | 'DEBIT' | 'CASH',
    receivedAmount?: number,
  ) => Promise<unknown>
  onDeliverOrder: () => Promise<unknown>
  onCancelOrder: () => Promise<unknown>
}

const getItemPrice = (item: MenuItem): number => {
  if (item.price !== undefined && item.price !== null) {
    return Number(item.price)
  }
  const base = 12.0
  const offset = (item.id % 6) * 5.5
  return base + offset
}

interface CatalogViewProps {
  searchQuery: string
  setSearchQuery: (q: string) => void
  selectedCategory: string
  setSelectedCategory: (c: string) => void
  setIsQuickSearchOpen: (open: boolean) => void
  categories: string[]
  filteredCatalogItems: MenuItem[]
  handleItemPressStart: (item: MenuItem) => void
  handleItemPressEnd: (item: MenuItem) => void
}

function CatalogView({
  searchQuery,
  setSearchQuery,
  selectedCategory,
  setSelectedCategory,
  setIsQuickSearchOpen,
  categories,
  filteredCatalogItems,
  handleItemPressStart,
  handleItemPressEnd,
}: CatalogViewProps) {
  return (
    <div className="flex-1 flex flex-col overflow-hidden border-b border-gray-900/60">
      {/* Search bar & Quick search trigger */}
      <div className="px-4 pt-3 flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Filtrar pratos, bebidas..."
            className="w-full bg-gray-900/20 pl-9 pr-4 py-2 text-xs text-white placeholder-gray-600 glass-input"
          />
        </div>
        <button
          type="button"
          onClick={() => setIsQuickSearchOpen(true)}
          className="rounded-xl border border-gray-800 bg-gray-900/40 hover:border-gray-700 px-3 py-2 text-xs text-gray-400 hover:text-white transition flex items-center gap-1.5"
          title="Busca Rápida (Teclado)"
        >
          <Sparkles className="h-3.5 w-3.5 text-brand-400 animate-pulse" />
          <span>Atalho</span>
        </button>
      </div>

      {/* Categorias Horizontal Scroll */}
      <div className="px-4 py-3 flex gap-1.5 overflow-x-auto scrollbar-none flex-shrink-0">
        {categories.map((cat) => {
          const isActive = selectedCategory === cat
          return (
            <button
              type="button"
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-3.5 py-1.5 rounded-full text-[10px] font-extrabold uppercase tracking-wider transition-all duration-300 flex-shrink-0 ${
                isActive
                  ? 'bg-brand-500 text-white shadow-md shadow-brand-500/10'
                  : 'bg-white/[0.02] border border-gray-900 text-gray-400 hover:text-gray-200'
              }`}
            >
              {cat}
            </button>
          )
        })}
      </div>

      {/* Grid de Itens Scrollable */}
      <div className="flex-1 overflow-y-auto px-4 pb-4 grid grid-cols-2 gap-2.5">
        {filteredCatalogItems.map((item) => {
          const price = getItemPrice(item)
          return (
            <button
              type="button"
              key={item.id}
              className="rounded-xl border border-gray-900 bg-gray-950/20 p-2.5 flex flex-col justify-between hover:border-gray-855 hover:bg-white/[0.01] transition-all duration-300 relative group cursor-pointer text-left w-full h-full"
              onMouseDown={() => handleItemPressStart(item)}
              onMouseUp={() => handleItemPressEnd(item)}
              onTouchStart={() => handleItemPressStart(item)}
              onTouchEnd={() => handleItemPressEnd(item)}
            >
              <div className="space-y-0.5">
                <span className="text-[8px] font-extrabold uppercase tracking-wider text-brand-400/80">
                  {item.category}
                </span>
                <h4 className="text-[11px] font-bold text-gray-100 group-hover:text-white line-clamp-1">
                  {item.name}
                </h4>
              </div>
              <div className="flex items-center justify-between mt-3.5 w-full">
                <span className="text-xs font-black text-amber-500">R$ {price.toFixed(2)}</span>
                <div className="h-6 w-6 rounded-lg bg-brand-500/10 border border-brand-500/20 flex items-center justify-center text-brand-400 group-hover:bg-brand-500 group-hover:text-white transition-all duration-300">
                  <Plus className="h-3.5 w-3.5" />
                </div>
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}

interface DraftItemsListProps {
  draft: DraftItem[]
  isSubmitting: boolean
  draftTotal: number
  onUpdateDraftQuantity: (itemId: number, delta: number) => void
  onUpdateDraftNotes: (itemId: number, notes: string) => void
  onSendToKitchen: () => Promise<unknown>
}

function DraftItemsList({
  draft,
  isSubmitting,
  draftTotal,
  onUpdateDraftQuantity,
  onUpdateDraftNotes,
  onSendToKitchen,
}: DraftItemsListProps) {
  return (
    <div className="p-4 border-b border-brand-500/20 bg-brand-950/5 space-y-3.5">
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-extrabold uppercase tracking-widest text-brand-400">
          Rascunho de Pedido
        </span>
        <span className="text-[10px] font-bold text-gray-400">{draft.length} novos itens</span>
      </div>
      <div className="space-y-2 max-h-[180px] overflow-y-auto pr-1">
        {draft.map((item) => (
          <div
            key={item.menuItem.id}
            className="rounded-xl border border-gray-900 bg-gray-950/40 p-2.5 space-y-2"
          >
            <div className="flex items-start justify-between">
              <div>
                <h4 className="text-[11px] font-bold text-gray-200">{item.menuItem.name}</h4>
                <span className="text-[10px] font-bold text-amber-500">
                  R$ {item.price.toFixed(2)}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => onUpdateDraftQuantity(item.menuItem.id, -1)}
                  className="h-6 w-6 rounded bg-gray-900 border border-gray-800 flex items-center justify-center text-xs font-bold text-white hover:border-gray-700"
                >
                  -
                </button>
                <span className="text-xs font-bold text-white w-4 text-center">
                  {item.quantity}
                </span>
                <button
                  type="button"
                  onClick={() => onUpdateDraftQuantity(item.menuItem.id, 1)}
                  className="h-6 w-6 rounded bg-gray-900 border border-gray-800 flex items-center justify-center text-xs font-bold text-white hover:border-gray-700"
                >
                  +
                </button>
              </div>
            </div>
            <input
              type="text"
              placeholder="Observações adicionais..."
              value={item.notes}
              onChange={(e) => onUpdateDraftNotes(item.menuItem.id, e.target.value)}
              className="w-full rounded-lg border border-gray-900 bg-gray-950 px-2 py-1.5 text-[10px] text-white placeholder-gray-600 focus:border-brand-500 focus:outline-none"
            />
          </div>
        ))}
      </div>

      <div className="flex gap-2">
        <button
          type="button"
          disabled={isSubmitting}
          onClick={onSendToKitchen}
          className="w-full flex items-center justify-center gap-1.5 rounded-xl bg-emerald-500 hover:bg-emerald-600 disabled:bg-gray-850 disabled:text-gray-500 py-3 text-xs font-bold text-white transition-all duration-300 shadow-md shadow-emerald-500/10"
        >
          {isSubmitting ? (
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
          ) : (
            <>
              <Send className="h-3.5 w-3.5" />
              Enviar p/ Cozinha (R$ {draftTotal.toFixed(2)})
            </>
          )}
        </button>
      </div>
    </div>
  )
}

interface ConfirmedItemsListProps {
  activeOrder: OrderForm
  isPaid: boolean
  isPaymentRequested: boolean
  isDelivering: boolean
  isProcessingPayment: boolean
  isCancelling: boolean
  isRequestingPayment: boolean
  onDeliverOrder: () => Promise<unknown>
  onCancelOrder: () => Promise<unknown>
  onRequestPayment: () => Promise<unknown>
  setIsPaymentOpen: (open: boolean) => void
}

const statusConfig: Record<string, { label: string; color: string }> = {
  WAITING: { label: 'Espera', color: 'border-amber-500/20 bg-amber-950/20 text-amber-400' },
  PREPARING: { label: 'Preparando', color: 'border-blue-500/20 bg-blue-950/20 text-blue-400' },
  READY: { label: 'Pronto', color: 'border-emerald-500/20 bg-emerald-950/20 text-emerald-400' },
  DELIVERED: { label: 'Servido', color: 'border-purple-500/20 bg-purple-950/20 text-purple-400' },
  CANCELED: { label: 'Cancelado', color: 'border-gray-500/20 bg-gray-950/20 text-gray-400' },
}

function ConfirmedItemsList({
  activeOrder,
  isPaid,
  isPaymentRequested,
  isDelivering,
  isProcessingPayment,
  isCancelling,
  isRequestingPayment,
  onDeliverOrder,
  onCancelOrder,
  onRequestPayment,
  setIsPaymentOpen,
}: ConfirmedItemsListProps) {
  return (
    <div className="p-4 flex-1 flex flex-col justify-between">
      <div>
        <span className="block text-[10px] font-extrabold uppercase tracking-widest text-gray-500 mb-3">
          Consumo Registrado
        </span>
        {activeOrder.items.length === 0 ? (
          <div className="flex flex-col items-center justify-center text-center text-xs text-gray-600 py-8">
            Nenhum item consumido ainda nesta mesa.
          </div>
        ) : (
          <div className="space-y-2.5 max-h-[300px] overflow-y-auto pr-1">
            {activeOrder.items.map((item) => (
              <div
                key={item.id}
                className="flex justify-between border-b border-gray-900/60 pb-2 text-xs"
              >
                <div className="space-y-0.5 min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    {item.kitchen_states && item.kitchen_states.length > 0 ? (
                      <div className="flex gap-1 flex-wrap">
                        {Object.entries(
                          item.kitchen_states.reduce(
                            (acc, st) => {
                              acc[st] = (acc[st] || 0) + 1
                              return acc
                            },
                            {} as Record<string, number>,
                          ),
                        ).map(([st, count]) => (
                          <span
                            key={st}
                            className={`rounded-full px-1.5 py-0.5 text-[8px] font-extrabold uppercase tracking-wider border ${
                              statusConfig[st]?.color ||
                              'border-gray-500/20 bg-gray-950/20 text-gray-400'
                            }`}
                            title={`${count}x unidades em status ${statusConfig[st]?.label || st}`}
                          >
                            {count > 1 ? `${count}x ` : ''}
                            {statusConfig[st]?.label || st}
                          </span>
                        ))}
                      </div>
                    ) : item.status ? (
                      <span
                        className={`rounded-full px-1.5 py-0.5 text-[8px] font-extrabold uppercase tracking-wider border ${
                          statusConfig[item.status]?.color ||
                          'border-gray-500/20 bg-gray-950/20 text-gray-400'
                        }`}
                      >
                        {statusConfig[item.status]?.label || item.status}
                      </span>
                    ) : null}
                    <h4 className="font-bold text-gray-200 truncate">{item.name_cpy}</h4>
                    <span className="text-gray-500 font-medium shrink-0">x{item.quantity}</span>
                  </div>
                  {item.notes && (
                    <span className="text-[9px] italic text-brand-400 font-medium block mt-1">
                      Obs: {item.notes}
                    </span>
                  )}
                </div>
                <span className="font-bold text-gray-400 shrink-0 ml-3">
                  R$ {Number(item.subtotal).toFixed(2)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="border-t border-gray-900 pt-3 space-y-4">
        <div className="flex items-center justify-between text-xs font-bold">
          <span className="text-gray-400">Total Acumulado</span>
          <span className="text-white text-sm font-black">
            R$ {Number(activeOrder.total).toFixed(2)}
          </span>
        </div>

        {/* Operational checkout buttons */}
        <div className="flex gap-2.5">
          {isPaid ? (
            /* Close table/checkout deliver */
            <button
              type="button"
              disabled={isDelivering}
              onClick={onDeliverOrder}
              className="w-full flex items-center justify-center gap-1.5 rounded-xl bg-purple-600 hover:bg-purple-700 py-3 text-xs font-bold text-white transition-all duration-300"
            >
              {isDelivering ? (
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              ) : (
                <>
                  <Check className="h-4 w-4" />
                  Desocupar & Liberar Mesa
                </>
              )}
            </button>
          ) : isPaymentRequested ? (
            /* Request payment details / Process payment */
            <button
              type="button"
              disabled={isProcessingPayment}
              onClick={() => setIsPaymentOpen(true)}
              className="w-full flex items-center justify-center gap-1.5 rounded-xl bg-blue-600 hover:bg-blue-700 py-3 text-xs font-bold text-white transition-all duration-300"
            >
              {isProcessingPayment ? (
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              ) : (
                <>
                  <DollarSign className="h-4 w-4" />
                  Processar Pagamento
                </>
              )}
            </button>
          ) : (
            /* Request count / cancel comanda */
            <>
              <button
                type="button"
                disabled={isCancelling}
                onClick={onCancelOrder}
                className="flex-1 flex items-center justify-center gap-1.5 rounded-xl border border-red-950/40 bg-red-950/10 hover:bg-red-900/20 py-3 text-xs font-bold text-red-400 transition"
              >
                <Ban className="h-3.5 w-3.5" />
                Cancelar
              </button>
              <button
                type="button"
                disabled={isRequestingPayment}
                onClick={onRequestPayment}
                className="flex-grow flex items-center justify-center gap-1.5 rounded-xl bg-brand-500 hover:bg-brand-600 py-3 text-xs font-bold text-white transition"
              >
                <DollarSign className="h-3.5 w-3.5" />
                Pedir Conta
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

interface OrderDrawerHeaderProps {
  order: OrderForm | null
  isOccupied: boolean
  isPaid: boolean
  isPaymentRequested: boolean
  onClose: () => void
}

function getHeaderTitle(order: OrderForm | null): { title: string; subtitle: string } {
  if (!order) return { title: 'Nova Comanda', subtitle: 'Preencha os detalhes para iniciar' }

  const displayCode =
    order.display_code && order.display_code !== String(order.id) ? order.display_code : ''
  const f = order.fulfillment
  if (f.type === 'TABLE' && f.table_number) {
    return {
      title: `Mesa ${f.table_number < 10 ? `0${f.table_number}` : f.table_number}`,
      subtitle: displayCode,
    }
  }
  if (f.type === 'TAKEAWAY') {
    return {
      title: f.customer_name || 'Retirada',
      subtitle: displayCode ? `${displayCode} · Retirada` : 'Retirada',
    }
  }
  if (f.type === 'DELIVERY') {
    return {
      title: displayCode || `Delivery #${order.id}`,
      subtitle: [f.delivery_street, f.delivery_number].filter(Boolean).join(', ') || 'Entrega',
    }
  }
  return { title: displayCode || `Comanda #${order.id}`, subtitle: '' }
}

function OrderDrawerHeader({
  order,
  isOccupied,
  isPaid,
  isPaymentRequested,
  onClose,
}: OrderDrawerHeaderProps) {
  const { title, subtitle } = getHeaderTitle(order)
  return (
    <div className="flex items-center justify-between px-6 py-4.5 border-b border-gray-900/60">
      <div>
        <div className="flex items-center gap-2">
          <h2 className="text-base font-black text-white">{title}</h2>
          {isOccupied && order && (
            <span
              className={`px-2 py-0.5 rounded-full text-[9px] font-extrabold uppercase tracking-wider border ${
                isPaid
                  ? 'border-purple-500/20 bg-purple-950/20 text-purple-400'
                  : isPaymentRequested
                    ? 'border-blue-500/20 bg-blue-950/20 text-blue-400'
                    : 'border-amber-500/20 bg-amber-950/20 text-amber-400'
              }`}
            >
              {isPaid ? 'Pago' : isPaymentRequested ? 'Conta Pedida' : 'Ativo'}
            </span>
          )}
        </div>
        <p className="text-[10px] text-gray-550 font-medium mt-0.5">
          {subtitle || (isOccupied ? 'Comanda aberta' : 'Nova comanda')}
        </p>
      </div>
      <button
        type="button"
        onClick={onClose}
        className="rounded-lg p-2 text-gray-550 hover:text-white transition bg-white/[0.02]"
      >
        <X className="h-4.5 w-4.5" />
      </button>
    </div>
  )
}

interface OrderDrawerLivreStateProps {
  onCreateOrder: (options: {
    display_code?: string
    fulfillment_type: 'TABLE' | 'TAKEAWAY' | 'DELIVERY'
    table_number?: number | null
    customer_name?: string
    delivery_street?: string
    delivery_number?: string
    delivery_neighborhood?: string
    delivery_city?: string
    delivery_state?: string
    delivery_postal_code?: string
    delivery_estimated_time?: number
    delivery_tracking_code?: number
  }) => void
}

function OrderDrawerLivreState({ onCreateOrder }: OrderDrawerLivreStateProps) {
  const [fulfillmentType, setFulfillmentType] = useState<'TABLE' | 'TAKEAWAY' | 'DELIVERY'>('TABLE')
  const [tableNumber, setTableNumber] = useState('1')
  const [customerName, setCustomerName] = useState('')
  const [street, setStreet] = useState('')
  const [number, setNumber] = useState('')
  const [neighborhood, setNeighborhood] = useState('')
  const [city, setCity] = useState('')
  const [stateCode, setStateCode] = useState('')
  const [postalCode, setPostalCode] = useState('')
  const [displayCode, setDisplayCode] = useState('')
  const [estTime, setEstTime] = useState('40')

  const validateForm = () => {
    if (fulfillmentType === 'TAKEAWAY' && !customerName.trim()) {
      alert('Por favor, informe o nome do cliente.')
      return false
    }
    if (fulfillmentType === 'DELIVERY') {
      const hasAddress =
        street.trim() && number.trim() && city.trim() && stateCode.trim() && postalCode.trim()
      if (!hasAddress) {
        alert('Por favor, preencha todos os campos do endereço de entrega.')
        return false
      }
    }
    return true
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!validateForm()) return

    const payload: {
      display_code?: string
      fulfillment_type: 'TABLE' | 'TAKEAWAY' | 'DELIVERY'
      table_number?: number | null
      customer_name?: string
      delivery_street?: string
      delivery_number?: string
      delivery_neighborhood?: string
      delivery_city?: string
      delivery_state?: string
      delivery_postal_code?: string
      delivery_estimated_time?: number
      delivery_tracking_code?: number
    } = {
      fulfillment_type: fulfillmentType,
    }

    if (displayCode.trim()) {
      payload.display_code = displayCode.trim()
    }

    if (fulfillmentType === 'TABLE') {
      payload.table_number = Number.parseInt(tableNumber, 10) || 1
    } else if (fulfillmentType === 'TAKEAWAY') {
      payload.customer_name = customerName
    } else if (fulfillmentType === 'DELIVERY') {
      payload.delivery_street = street
      payload.delivery_number = number
      payload.delivery_neighborhood = neighborhood
      payload.delivery_city = city
      payload.delivery_state = stateCode
      payload.delivery_postal_code = postalCode
      payload.delivery_estimated_time = Number.parseInt(estTime, 10) || 40
    }

    onCreateOrder(payload)
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex-1 flex flex-col justify-between p-6 overflow-y-auto space-y-5"
    >
      <div className="space-y-4">
        <div className="flex flex-col items-center text-center space-y-2">
          <div className="h-12 w-12 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
            <Check className="h-6 w-6" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-gray-200">Novo Pedido / Comanda</h3>
            <p className="text-[11px] text-gray-550 max-w-xs mt-0.5">
              Escolha a modalidade de atendimento e preencha os detalhes para iniciar
            </p>
          </div>
        </div>

        <div className="space-y-3">
          <div className="space-y-1.5">
            <span className="block text-[10px] uppercase font-extrabold text-gray-400">
              Tipo de Atendimento
            </span>
            <select
              value={fulfillmentType}
              onChange={(e) =>
                setFulfillmentType(e.target.value as 'TABLE' | 'TAKEAWAY' | 'DELIVERY')
              }
              className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input bg-[#0b0b11]"
            >
              <option value="TABLE">Mesa / Consumo Local</option>
              <option value="TAKEAWAY">Retirada (Takeaway)</option>
              <option value="DELIVERY">Entrega (Delivery)</option>
            </select>
          </div>

          <div className="space-y-1.5">
            <span className="block text-[10px] uppercase font-extrabold text-gray-400">
              Nº da Comanda <span className="text-gray-600">(opcional)</span>
            </span>
            <input
              type="text"
              placeholder={fulfillmentType === 'TABLE' ? 'Ex: MESA-04' : 'Ex: RET-123'}
              value={displayCode}
              onChange={(e) => setDisplayCode(e.target.value)}
              className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input"
            />
          </div>

          {fulfillmentType === 'TABLE' && (
            <div className="space-y-1.5 animate-fade-in">
              <span className="block text-[10px] uppercase font-extrabold text-gray-400">
                Número da Mesa
              </span>
              <input
                type="number"
                required
                min="1"
                placeholder="Ex: 1"
                value={tableNumber}
                onChange={(e) => setTableNumber(e.target.value)}
                className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input"
              />
            </div>
          )}

          {fulfillmentType === 'TAKEAWAY' && (
            <div className="space-y-1.5 animate-fade-in">
              <span className="block text-[10px] uppercase font-extrabold text-gray-400">
                Nome do Cliente
              </span>
              <input
                type="text"
                required
                placeholder="Ex: Carlos Silva"
                value={customerName}
                onChange={(e) => setCustomerName(e.target.value)}
                className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input"
              />
            </div>
          )}

          {fulfillmentType === 'DELIVERY' && (
            <div className="space-y-3 animate-fade-in">
              <div className="grid grid-cols-3 gap-2">
                <div className="col-span-2 space-y-1.5">
                  <span className="block text-[10px] uppercase font-extrabold text-gray-400">
                    Logradouro / Rua
                  </span>
                  <input
                    type="text"
                    required
                    placeholder="Av. Paulista"
                    value={street}
                    onChange={(e) => setStreet(e.target.value)}
                    className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input"
                  />
                </div>
                <div className="col-span-1 space-y-1.5">
                  <span className="block text-[10px] uppercase font-extrabold text-gray-400">
                    Número
                  </span>
                  <input
                    type="text"
                    required
                    placeholder="1000"
                    value={number}
                    onChange={(e) => setNumber(e.target.value)}
                    className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-1.5">
                  <span className="block text-[10px] uppercase font-extrabold text-gray-400">
                    Bairro
                  </span>
                  <input
                    type="text"
                    placeholder="Bela Vista"
                    value={neighborhood}
                    onChange={(e) => setNeighborhood(e.target.value)}
                    className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input"
                  />
                </div>
                <div className="space-y-1.5">
                  <span className="block text-[10px] uppercase font-extrabold text-gray-400">
                    CEP
                  </span>
                  <input
                    type="text"
                    required
                    placeholder="01311-000"
                    value={postalCode}
                    onChange={(e) => setPostalCode(e.target.value)}
                    className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-2">
                <div className="col-span-2 space-y-1.5">
                  <span className="block text-[10px] uppercase font-extrabold text-gray-400">
                    Cidade
                  </span>
                  <input
                    type="text"
                    required
                    placeholder="São Paulo"
                    value={city}
                    onChange={(e) => setCity(e.target.value)}
                    className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input"
                  />
                </div>
                <div className="col-span-1 space-y-1.5">
                  <span className="block text-[10px] uppercase font-extrabold text-gray-400">
                    UF
                  </span>
                  <input
                    type="text"
                    required
                    maxLength={2}
                    placeholder="SP"
                    value={stateCode}
                    onChange={(e) => setStateCode(e.target.value.toUpperCase())}
                    className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input text-center"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <span className="block text-[10px] uppercase font-extrabold text-gray-400">
                  Tempo Estimado (minutos)
                </span>
                <input
                  type="number"
                  required
                  value={estTime}
                  onChange={(e) => setEstTime(e.target.value)}
                  className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input"
                />
              </div>
            </div>
          )}
        </div>
      </div>

      <button
        type="submit"
        className="w-full rounded-xl bg-brand-500 hover:bg-brand-600 py-3 text-xs font-bold text-white transition-all shadow-lg shadow-brand-500/15 flex items-center justify-center gap-1.5"
      >
        <Plus className="h-4 w-4" />
        Iniciar Pedido / Comanda
      </button>
    </form>
  )
}

export default function OrderDrawer({
  order: activeOrder,
  draft,
  activeMenu,
  isLoading,
  isSubmitting,
  isRequestingPayment,
  isProcessingPayment,
  isCancelling,
  isDelivering,
  onClose,
  onCreateOrder,
  onSelectItem,
  onUpdateDraftQuantity,
  onUpdateDraftNotes,
  onSendToKitchen,
  onRequestPayment,
  onProcessPayment,
  onDeliverOrder,
  onCancelOrder,
}: OrderDrawerProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('Todos')
  const [selectedModifierItem, setSelectedModifierItem] = useState<MenuItem | null>(null)
  const [isModifierOpen, setIsModifierOpen] = useState(false)
  const [isPaymentOpen, setIsPaymentOpen] = useState(false)
  const [isQuickSearchOpen, setIsQuickSearchOpen] = useState(false)

  const longPressTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Long press helpers for modifiers picker on Catalog
  const handleItemPressStart = (item: MenuItem) => {
    longPressTimer.current = setTimeout(() => {
      setSelectedModifierItem(item)
      setIsModifierOpen(true)
      longPressTimer.current = null
    }, 550)
  }

  const handleItemPressEnd = (item: MenuItem) => {
    if (longPressTimer.current) {
      clearTimeout(longPressTimer.current)
      longPressTimer.current = null
      onSelectItem(item)
    }
  }

  const handleModifierConfirm = (notes: string) => {
    if (!selectedModifierItem) return
    onSelectItem(selectedModifierItem)
    setTimeout(() => {
      onUpdateDraftNotes(selectedModifierItem.id, notes)
    }, 10)
  }

  // Pre-process categories
  const categories: string[] = activeMenu
    ? [
        'Todos',
        ...Array.from(new Set<string>(activeMenu.items.map((item: MenuItem) => item.category))),
      ]
    : ['Todos']

  // Pre-process items based on category and search
  const filteredCatalogItems: MenuItem[] = activeMenu
    ? activeMenu.items.filter((item: MenuItem) => {
        const matchesCategory = selectedCategory === 'Todos' || item.category === selectedCategory
        const matchesSearch = item.name.toLowerCase().includes(searchQuery.toLowerCase())
        return matchesCategory && matchesSearch && item.is_available
      })
    : []

  const draftTotal = draft.reduce((sum, d) => sum + d.price * d.quantity, 0)
  const isOccupied = activeOrder !== null
  const isPaymentRequested = !!activeOrder?.payment_requested
  const isPaid = activeOrder?.state === 'PAID'

  return (
    <div className="flex flex-col h-full bg-gray-950/95 border-l border-gray-900 glass-elevated animate-slide-in-right select-none">
      <OrderDrawerHeader
        order={activeOrder}
        isOccupied={isOccupied}
        isPaid={isPaid}
        isPaymentRequested={isPaymentRequested}
        onClose={onClose}
      />

      {isLoading ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-500 border-t-transparent" />
        </div>
      ) : !isOccupied ? (
        <OrderDrawerLivreState onCreateOrder={onCreateOrder} />
      ) : (
        <div className="flex-1 flex flex-col overflow-hidden min-h-0">
          {!isPaymentRequested && !isPaid && (
            <CatalogView
              searchQuery={searchQuery}
              setSearchQuery={setSearchQuery}
              selectedCategory={selectedCategory}
              setSelectedCategory={setSelectedCategory}
              setIsQuickSearchOpen={setIsQuickSearchOpen}
              categories={categories}
              filteredCatalogItems={filteredCatalogItems}
              handleItemPressStart={handleItemPressStart}
              handleItemPressEnd={handleItemPressEnd}
            />
          )}

          <div className="flex-grow flex flex-col overflow-y-auto min-h-0 bg-gray-950/40">
            {draft.length > 0 && (
              <DraftItemsList
                draft={draft}
                isSubmitting={isSubmitting}
                draftTotal={draftTotal}
                onUpdateDraftQuantity={onUpdateDraftQuantity}
                onUpdateDraftNotes={onUpdateDraftNotes}
                onSendToKitchen={onSendToKitchen}
              />
            )}

            <ConfirmedItemsList
              activeOrder={activeOrder}
              isPaid={isPaid}
              isPaymentRequested={isPaymentRequested}
              isDelivering={isDelivering}
              isProcessingPayment={isProcessingPayment}
              isCancelling={isCancelling}
              isRequestingPayment={isRequestingPayment}
              onDeliverOrder={onDeliverOrder}
              onCancelOrder={onCancelOrder}
              onRequestPayment={onRequestPayment}
              setIsPaymentOpen={setIsPaymentOpen}
            />
          </div>
        </div>
      )}

      {/* Modals & Overlays */}
      <ModifierPicker
        isOpen={isModifierOpen}
        onClose={() => setIsModifierOpen(false)}
        itemName={selectedModifierItem?.name || ''}
        category={selectedModifierItem?.category || ''}
        initialNotes=""
        onConfirm={handleModifierConfirm}
      />

      <PaymentModal
        isOpen={isPaymentOpen}
        onClose={() => setIsPaymentOpen(false)}
        total={activeOrder ? Number(activeOrder.total) : 0}
        onConfirm={onProcessPayment}
      />

      <QuickSearch
        isOpen={isQuickSearchOpen}
        onClose={() => setIsQuickSearchOpen(false)}
        menuItems={activeMenu ? activeMenu.items : []}
        onSelectItem={onSelectItem}
      />
    </div>
  )
}
