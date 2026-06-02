import { useState } from 'react'
import OrderDraft from '@/features/order/components/order_draft'
import TableGrid from '@/features/order/components/table_grid'
import CheckoutFlow from '@/features/payment/components/checkout_flow'
import Layout from '@/shared/components/layout'

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

export default function OrdersPage() {
  const [selectedTable, setSelectedTable] = useState<number | null>(null)
  const [activeOrder, setActiveOrder] = useState<OrderForm | null>(null)

  const handleSelectTable = (tableNumber: number, order: OrderForm | null) => {
    setSelectedTable(tableNumber)
    setActiveOrder(order)
  }

  const handleBackToGrid = () => {
    setSelectedTable(null)
    setActiveOrder(null)
  }

  const handleOrderUpdated = (updatedOrder: OrderForm) => {
    setActiveOrder(updatedOrder)
  }

  const handleNavigateToCheckout = () => {
    if (activeOrder) {
      setActiveOrder({
        ...activeOrder,
        payment_requested: true,
      })
    }
  }

  return (
    <Layout>
      {selectedTable === null || activeOrder === null ? (
        <TableGrid onSelectTable={handleSelectTable} />
      ) : activeOrder.payment_requested && activeOrder.state !== 'PAID' ? (
        <CheckoutFlow
          tableNumber={selectedTable}
          order={activeOrder}
          onBack={handleBackToGrid}
          onPaymentCompleted={handleBackToGrid}
        />
      ) : (
        <OrderDraft
          tableNumber={selectedTable}
          activeOrder={activeOrder}
          onBack={handleBackToGrid}
          onOrderUpdated={handleOrderUpdated}
          onNavigateToCheckout={handleNavigateToCheckout}
        />
      )}
    </Layout>
  )
}
