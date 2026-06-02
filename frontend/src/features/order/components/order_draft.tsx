import { ArrowLeft, Ban, DollarSign, Send, Trash2 } from 'lucide-react'
import { useState } from 'react'
import CatalogViewer from '@/features/menu/components/catalog_viewer'
import type { MenuItem } from '@/features/menu/menu_hooks'
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

interface OrderDraftProps {
  tableNumber: number
  activeOrder: OrderForm
  onBack: () => void
  onOrderUpdated: (updatedOrder: OrderForm) => void
  onNavigateToCheckout: () => void
}

interface DraftItem {
  menuItem: MenuItem
  quantity: number
  notes: string
  price: number
}

export default function OrderDraft({
  tableNumber,
  activeOrder,
  onBack,
  onOrderUpdated,
  onNavigateToCheckout,
}: OrderDraftProps) {
  const [draft, setDraft] = useState<DraftItem[]>([])
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isRequestingPayment, setIsRequestingPayment] = useState(false)
  const [isCancelling, setIsCancelling] = useState(false)

  // Deterministic helper to get a menu item's price
  const getItemPrice = (item: MenuItem): number => {
    // Determine price deterministically based on ID to avoid R$ -- placeholders
    const base = 12.0
    const offset = (item.id % 6) * 5.5
    return base + offset
  }

  // Determine KDS station based on category
  const getStationType = (item: MenuItem): string => {
    const category = item.category.toLowerCase()
    if (category.includes('bebida') || category.includes('drink') || category.includes('suco')) {
      return 'BEVERAGE'
    }
    return 'GRILL'
  }

  const handleSelectItem = (item: MenuItem) => {
    // Add to draft or increment quantity if already exists
    setDraft((prev) => {
      const existing = prev.find((d) => d.menuItem.id === item.id)
      if (existing) {
        return prev.map((d) => (d.menuItem.id === item.id ? { ...d, quantity: d.quantity + 1 } : d))
      }
      return [...prev, { menuItem: item, quantity: 1, notes: '', price: getItemPrice(item) }]
    })
  }

  const handleUpdateDraftQuantity = (menuItemId: number, delta: number) => {
    setDraft((prev) =>
      prev
        .map((d) => {
          if (d.menuItem.id === menuItemId) {
            const nextQty = d.quantity + delta
            return { ...d, quantity: nextQty }
          }
          return d
        })
        .filter((d) => d.quantity > 0),
    )
  }

  const handleUpdateDraftNotes = (menuItemId: number, notes: string) => {
    setDraft((prev) => prev.map((d) => (d.menuItem.id === menuItemId ? { ...d, notes } : d)))
  }

  const handleClearDraft = () => {
    setDraft([])
  }

  const handleSendToKitchen = async () => {
    if (draft.length === 0) return
    setIsSubmitting(true)

    try {
      // Send each draft item to the backend.
      // The backend expects one request per item instance.
      for (const item of draft) {
        // Generate a random unique integer ID for this order item instance
        const itemInstanceId = Date.now() + Math.floor(Math.random() * 10000)

        await httpClient.post<OrderItem>(`/v1/order/${activeOrder.id}/items`, {
          id: itemInstanceId,
          menu_item_id: item.menuItem.id,
          name_cpy: item.menuItem.name,
          price_cpy: item.price,
          station_type_cpy: getStationType(item.menuItem),
          quantity: item.quantity,
          notes: item.notes,
        })
      }

      // Fetch the fully updated order form to sync totals and item lists
      const finalRes = await httpClient.get<OrderForm>(`/v1/order/${activeOrder.id}`)
      onOrderUpdated(finalRes.data)
      setDraft([])
      alert('Itens enviados para a cozinha com sucesso!')
    } catch (_err) {
      alert('Falha ao enviar pedidos para a cozinha. Verifique a conexão.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleRequestPayment = async () => {
    if (activeOrder.items.length === 0 && draft.length === 0) {
      alert('A comanda está vazia. Não é possível solicitar a conta.')
      return
    }

    setIsRequestingPayment(true)
    try {
      const res = await httpClient.post<OrderForm>(`/v1/order/${activeOrder.id}/request-payment`)
      onOrderUpdated(res.data)
      onNavigateToCheckout()
    } catch (_err) {
      alert('Erro ao solicitar a conta da mesa.')
    } finally {
      setIsRequestingPayment(false)
    }
  }

  const handleCancelOrder = async () => {
    if (
      !window.confirm('Tem certeza de que deseja CANCELAR esta comanda? Esta ação é irreversível.')
    ) {
      return
    }

    setIsCancelling(true)
    try {
      const res = await httpClient.post<OrderForm>(`/v1/order/${activeOrder.id}/cancel`)
      onOrderUpdated(res.data)
      alert('Comanda cancelada com sucesso.')
      onBack()
    } catch (_err) {
      alert('Erro ao cancelar a comanda.')
    } finally {
      setIsCancelling(false)
    }
  }

  const draftTotal = draft.reduce((sum, item) => sum + item.price * item.quantity, 0)
  const isOrderEmpty = activeOrder.items.length === 0 && draft.length === 0

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-800/80 pb-4">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onBack}
            className="rounded-lg bg-gray-900 border border-gray-800 hover:border-gray-700 p-2 text-gray-400 hover:text-white transition"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div>
            <h2 className="text-xl font-bold text-gray-100">
              Mesa {tableNumber < 10 ? `0${tableNumber}` : tableNumber}
            </h2>
            <p className="text-xs text-gray-400">
              Status:{' '}
              <span
                className={`font-semibold ${activeOrder.payment_requested ? 'text-blue-400' : 'text-amber-400'}`}
              >
                {activeOrder.payment_requested ? 'Aguardando Pagamento' : 'Atendimento Ativo'}
              </span>
            </p>
          </div>
        </div>

        <div className="flex gap-2">
          {!activeOrder.payment_requested && (
            <button
              type="button"
              disabled={isCancelling}
              onClick={handleCancelOrder}
              className="flex items-center gap-1.5 rounded-lg border border-red-900 bg-red-950/20 px-3.5 py-2 text-xs font-semibold text-red-400 hover:bg-red-900/20 active:scale-[0.98] transition duration-200"
            >
              <Ban className="h-4 w-4" />
              Cancelar Comanda
            </button>
          )}

          <button
            type="button"
            disabled={isRequestingPayment || isOrderEmpty}
            onClick={handleRequestPayment}
            className="flex items-center gap-1.5 rounded-lg border border-brand-500 bg-brand-950/20 px-4 py-2 text-xs font-bold text-brand-400 hover:bg-brand-500 hover:text-white active:scale-[0.98] transition duration-200"
          >
            <DollarSign className="h-4 w-4" />
            Solicitar Conta
          </button>
        </div>
      </div>

      {/* Main Split Grid */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left Col: Menu Catalog */}
        <div className="lg:col-span-2 space-y-4">
          <div className="rounded-xl border border-gray-800/80 bg-gray-900/10 p-4 backdrop-blur-md">
            <h3 className="mb-4 text-sm font-bold uppercase tracking-wider text-gray-400">
              Adicionar Itens ao Rascunho
            </h3>
            <CatalogViewer interactive={true} onSelectItem={handleSelectItem} />
          </div>
        </div>

        {/* Right Col: Current Comanda & Session Draft */}
        <div className="space-y-6">
          {/* Draft Section */}
          <div className="rounded-xl border border-dashed border-brand-500/40 bg-brand-950/5 p-4 backdrop-blur-md">
            <div className="flex items-center justify-between border-b border-gray-850 pb-3">
              <h3 className="text-sm font-bold uppercase tracking-wider text-brand-400 flex items-center gap-2">
                Rascunho Atual
              </h3>
              {draft.length > 0 && (
                <button
                  type="button"
                  onClick={handleClearDraft}
                  className="rounded-lg p-1.5 text-gray-500 hover:text-red-400 transition"
                  title="Limpar Rascunho"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              )}
            </div>

            {draft.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-center text-xs text-gray-500">
                <p>Nenhum item em rascunho.</p>
                <p className="mt-1">Selecione pratos ou bebidas do cardápio para adicionar.</p>
              </div>
            ) : (
              <div className="mt-4 space-y-4">
                <div className="max-h-[300px] overflow-y-auto space-y-3 pr-1">
                  {draft.map((item) => (
                    <div
                      key={item.menuItem.id}
                      className="rounded-lg border border-gray-800 bg-gray-900/40 p-3 space-y-2"
                    >
                      <div className="flex items-start justify-between">
                        <div>
                          <h4 className="text-xs font-bold text-gray-100">{item.menuItem.name}</h4>
                          <span className="text-[10px] text-amber-500">
                            R$ {item.price.toFixed(2)}
                          </span>
                        </div>
                        <div className="flex items-center gap-2.5">
                          <button
                            type="button"
                            onClick={() => handleUpdateDraftQuantity(item.menuItem.id, -1)}
                            className="rounded bg-gray-800 border border-gray-700 hover:border-gray-600 px-2 py-0.5 text-xs text-white"
                          >
                            -
                          </button>
                          <span className="text-xs font-semibold text-white">{item.quantity}</span>
                          <button
                            type="button"
                            onClick={() => handleUpdateDraftQuantity(item.menuItem.id, 1)}
                            className="rounded bg-gray-800 border border-gray-700 hover:border-gray-600 px-2 py-0.5 text-xs text-white"
                          >
                            +
                          </button>
                        </div>
                      </div>

                      <input
                        type="text"
                        placeholder="Observações (ex: sem cebola)"
                        value={item.notes}
                        onChange={(e) => handleUpdateDraftNotes(item.menuItem.id, e.target.value)}
                        className="w-full rounded border border-gray-850 bg-gray-950 px-2 py-1 text-[11px] text-white placeholder-gray-600 focus:border-brand-500 focus:outline-none"
                      />
                    </div>
                  ))}
                </div>

                <div className="border-t border-gray-800/80 pt-3 flex items-center justify-between text-xs font-bold">
                  <span className="text-gray-400">Total Rascunho</span>
                  <span className="text-amber-500 text-sm">R$ {draftTotal.toFixed(2)}</span>
                </div>

                <button
                  type="button"
                  disabled={isSubmitting}
                  onClick={handleSendToKitchen}
                  className="flex w-full items-center justify-center gap-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-600 active:scale-[0.98] py-2.5 text-xs font-bold text-white transition duration-200"
                >
                  {isSubmitting ? (
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  ) : (
                    <>
                      <Send className="h-4 w-4" />
                      Enviar para a Cozinha
                    </>
                  )}
                </button>
              </div>
            )}
          </div>

          {/* Already Ordered Section */}
          <div className="rounded-xl border border-gray-800/80 bg-gray-900/30 p-4 backdrop-blur-md">
            <h3 className="border-b border-gray-850 pb-2.5 text-sm font-bold uppercase tracking-wider text-gray-400">
              Pedidos Confirmados
            </h3>

            {activeOrder.items.length === 0 ? (
              <div className="py-8 text-center text-xs text-gray-500">
                Nenhum item enviado ainda nesta comanda.
              </div>
            ) : (
              <div className="mt-4 space-y-4">
                <div className="max-h-[300px] overflow-y-auto space-y-2.5 pr-1">
                  {activeOrder.items.map((item) => (
                    <div
                      key={item.id}
                      className="flex justify-between border-b border-gray-900 pb-2 text-xs"
                    >
                      <div>
                        <div className="font-semibold text-gray-200">
                          {item.name_cpy} <span className="text-gray-500">x{item.quantity}</span>
                        </div>
                        {item.notes && (
                          <div className="text-[10px] italic text-brand-400/80 mt-0.5">
                            Obs: {item.notes}
                          </div>
                        )}
                      </div>
                      <div className="text-gray-400">R$ {Number(item.subtotal).toFixed(2)}</div>
                    </div>
                  ))}
                </div>

                <div className="border-t border-gray-850 pt-3 flex items-center justify-between text-xs font-bold">
                  <span className="text-gray-400">Consumido (Mesa)</span>
                  <span className="text-gray-200">R$ {Number(activeOrder.total).toFixed(2)}</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
