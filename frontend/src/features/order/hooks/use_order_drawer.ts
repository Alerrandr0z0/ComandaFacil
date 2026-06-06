import { useCallback, useState } from 'react'
import type { MenuItem } from '@/features/menu/menu_hooks'
import { useActiveMenu } from '@/features/menu/menu_hooks'
import { httpClient } from '@/shared/lib/http_client'

export interface OrderFulfillment {
  type: string | null
  fee: string
  table_number?: number | null
}

export interface OrderItem {
  id: number
  menu_item_id: number
  name_cpy: string
  price_cpy: number
  quantity: number
  notes: string
  subtotal: number
}

export interface OrderForm {
  id: number
  tenant_id: string
  state: 'OPEN' | 'PAID' | 'CLOSED'
  payment_requested: boolean
  total: number
  fulfillment: OrderFulfillment
  items: OrderItem[]
}

export interface OpenTableOptions {
  fulfillment_type: 'TABLE' | 'TAKEAWAY' | 'DELIVERY'
  customer_name?: string
  delivery_street?: string
  delivery_number?: string
  delivery_neighborhood?: string
  delivery_city?: string
  delivery_state?: string
  delivery_postal_code?: string
  delivery_estimated_time?: number
  delivery_tracking_code?: number
}

function buildOpenTablePayload(tableNum: number, options?: OpenTableOptions) {
  const base = {
    id: tableNum + Math.floor(Math.random() * 1000000),
    fulfillment_type: 'TABLE',
    table_number: tableNum as number | null,
    customer_name: null as string | null,
    delivery_street: null as string | null,
    delivery_number: null as string | null,
    delivery_neighborhood: null as string | null,
    delivery_city: null as string | null,
    delivery_state: null as string | null,
    delivery_postal_code: null as string | null,
    delivery_estimated_time: 40,
    delivery_tracking_code: 0,
  }

  if (options) {
    base.fulfillment_type = options.fulfillment_type
    if (options.fulfillment_type !== 'TABLE') {
      base.table_number = null
    }
    if (options.customer_name) {
      base.customer_name = options.customer_name
    }
    if (options.delivery_street) {
      base.delivery_street = options.delivery_street
      base.delivery_number = options.delivery_number || null
      base.delivery_neighborhood = options.delivery_neighborhood || null
      base.delivery_city = options.delivery_city || null
      base.delivery_state = options.delivery_state || null
      base.delivery_postal_code = options.delivery_postal_code || null
      base.delivery_estimated_time = options.delivery_estimated_time || 40
      base.delivery_tracking_code = options.delivery_tracking_code || 0
    }
  }

  return base
}

export interface DraftItem {
  menuItem: MenuItem
  quantity: number
  notes: string
  price: number
}

// Helper price lookup based on ID
const getItemPrice = (item: MenuItem): number => {
  try {
    const pricesStr = localStorage.getItem('cf_menu_item_prices')
    if (pricesStr) {
      const prices = JSON.parse(pricesStr)
      if (prices[item.id] !== undefined) {
        return Number(prices[item.id])
      }
    }
  } catch (_e) {
    // Ignore and fallback
  }
  const base = 12.0
  const offset = (item.id % 6) * 5.5
  return base + offset
}

const getStationType = (item: MenuItem): string => {
  const category = item.category.toLowerCase()
  if (
    category.includes('bebida') ||
    category.includes('suco') ||
    category.includes('drink') ||
    category.includes('cerveja')
  ) {
    return 'BEVERAGE'
  }
  return 'GRILL'
}

export function useOrderDrawer() {
  const { data: activeMenu } = useActiveMenu()
  const [selectedTableNumber, setSelectedTableNumber] = useState<number | null>(null)
  const [activeOrder, setActiveOrder] = useState<OrderForm | null>(null)
  const [draft, setDraft] = useState<DraftItem[]>([])

  const [isLoading, setIsLoading] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isRequestingPayment, setIsRequestingPayment] = useState(false)
  const [isProcessingPayment, setIsProcessingPayment] = useState(false)
  const [isCancelling, setIsCancelling] = useState(false)
  const [isDelivering, setIsDelivering] = useState(false)

  // Fetch active order for the selected table
  const fetchActiveOrder = useCallback(async (tableNum: number) => {
    setIsLoading(true)
    try {
      const res = await httpClient.get<OrderForm>(`/v1/order/${tableNum}`)
      if (res.data.state === 'CLOSED') {
        setActiveOrder(null)
      } else {
        setActiveOrder(res.data)
      }
    } catch (err) {
      const errorObj = err as { response?: { status: number } }
      if (errorObj.response && errorObj.response.status === 404) {
        setActiveOrder(null)
      } else {
      }
    } finally {
      setIsLoading(false)
    }
  }, [])

  const selectTable = useCallback(
    (tableNum: number, existingOrder: OrderForm | null) => {
      setSelectedTableNumber(tableNum)
      setDraft([])
      if (existingOrder) {
        setActiveOrder(existingOrder)
      } else {
        fetchActiveOrder(tableNum)
      }
    },
    [fetchActiveOrder],
  )

  const closeDrawer = useCallback(() => {
    setSelectedTableNumber(null)
    setActiveOrder(null)
    setDraft([])
  }, [])

  const openTable = async (tableNum: number, options?: OpenTableOptions) => {
    setIsLoading(true)
    const payload = buildOpenTablePayload(tableNum, options)
    try {
      const res = await httpClient.post<OrderForm>('/v1/order', payload)
      setActiveOrder(res.data)
      setSelectedTableNumber(tableNum)
      setDraft([])
      return res.data
    } catch (err) {
      alert('Falha ao abrir o pedido. Tente novamente.')
      throw err
    } finally {
      setIsLoading(false)
    }
  }

  const handleSelectItem = useCallback((item: MenuItem) => {
    setDraft((prev) => {
      const existing = prev.find((d) => d.menuItem.id === item.id)
      if (existing) {
        return prev.map((d) => (d.menuItem.id === item.id ? { ...d, quantity: d.quantity + 1 } : d))
      }
      return [...prev, { menuItem: item, quantity: 1, notes: '', price: getItemPrice(item) }]
    })
  }, [])

  const updateDraftQuantity = useCallback((menuItemId: number, delta: number) => {
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
  }, [])

  const updateDraftNotes = useCallback((menuItemId: number, notes: string) => {
    setDraft((prev) => prev.map((d) => (d.menuItem.id === menuItemId ? { ...d, notes } : d)))
  }, [])

  const sendToKitchen = async () => {
    if (!activeOrder || draft.length === 0) return
    setIsSubmitting(true)

    try {
      for (const item of draft) {
        // Unique random ID for item instance
        const itemInstanceId = Date.now() + Math.floor(Math.random() * 10000)

        await httpClient.post(`/v1/order/${activeOrder.id}/items`, {
          id: itemInstanceId,
          menu_item_id: item.menuItem.id,
          name_cpy: item.menuItem.name,
          price_cpy: item.price,
          station_type_cpy: getStationType(item.menuItem),
          quantity: item.quantity,
          notes: item.notes,
        })
      }

      // Fetch the updated order state
      const finalRes = await httpClient.get<OrderForm>(`/v1/order/${activeOrder.id}`)
      setActiveOrder(finalRes.data)
      setDraft([])
      return finalRes.data
    } catch (err) {
      alert('Falha ao enviar pedidos para a cozinha.')
      throw err
    } finally {
      setIsSubmitting(false)
    }
  }

  const requestPayment = async () => {
    if (!activeOrder) return
    setIsRequestingPayment(true)
    try {
      const res = await httpClient.post<OrderForm>(`/v1/order/${activeOrder.id}/request-payment`)
      setActiveOrder(res.data)
      return res.data
    } catch (err) {
      alert('Erro ao solicitar a conta.')
      throw err
    } finally {
      setIsRequestingPayment(false)
    }
  }

  const processPayment = async (
    method: 'PIX' | 'CREDIT' | 'DEBIT' | 'CASH',
    _receivedAmount?: number,
  ) => {
    if (!activeOrder) return
    setIsProcessingPayment(true)
    try {
      // 1. Process payment via endpoint
      await httpClient.post(`/v1/payments/request`, {
        order_id: activeOrder.id,
        amount: activeOrder.total,
        payment_method: method,
      })

      // 2. Confirm order transition to PAID
      const res = await httpClient.post<OrderForm>(`/v1/order/${activeOrder.id}/process-payment`)
      setActiveOrder(res.data)
      return res.data
    } catch (err) {
      alert('Erro ao processar o pagamento.')
      throw err
    } finally {
      setIsProcessingPayment(false)
    }
  }

  const deliverOrder = async () => {
    if (!activeOrder) return
    setIsDelivering(true)
    try {
      const res = await httpClient.post<OrderForm>(`/v1/order/${activeOrder.id}/deliver`)
      setActiveOrder(null)
      setSelectedTableNumber(null)
      setDraft([])
      return res.data
    } catch (err) {
      alert('Erro ao fechar a comanda.')
      throw err
    } finally {
      setIsDelivering(false)
    }
  }

  const cancelOrder = async () => {
    if (!activeOrder) return
    setIsCancelling(true)
    try {
      const res = await httpClient.post<OrderForm>(`/v1/order/${activeOrder.id}/cancel`)
      setActiveOrder(null)
      setSelectedTableNumber(null)
      setDraft([])
      return res.data
    } catch (err) {
      alert('Erro ao cancelar a comanda.')
      throw err
    } finally {
      setIsCancelling(false)
    }
  }

  return {
    selectedTableNumber,
    activeOrder,
    draft,
    activeMenu,
    isLoading,
    isSubmitting,
    isRequestingPayment,
    isProcessingPayment,
    isCancelling,
    isDelivering,
    selectTable,
    closeDrawer,
    openTable,
    handleSelectItem,
    updateDraftQuantity,
    updateDraftNotes,
    sendToKitchen,
    requestPayment,
    processPayment,
    deliverOrder,
    cancelOrder,
    fetchActiveOrder,
  }
}
