import { BellRing, Coffee } from 'lucide-react'
import { useState } from 'react'
import OrderDrawer from '@/features/order/components/order_drawer'
import OrderGrid from '@/features/order/components/order_grid'
import { useKitchenAlerts } from '@/features/order/hooks/use_kitchen_alerts'
import { useOrderDrawer } from '@/features/order/hooks/use_order_drawer'
import Layout from '@/shared/components/layout'

export default function OrdersPage() {
  const [refreshKey, setRefreshKey] = useState(0)
  const drawer = useOrderDrawer(() => setRefreshKey((k) => k + 1))
  const { readyItems, dismissReadyItem } = useKitchenAlerts()
  const [activeOrdersCount, setActiveOrdersCount] = useState(0)

  const hasActiveOrder = drawer.selectedOrderId !== null

  return (
    <Layout>
      <div className="flex h-full gap-6 relative">
        <div
          className={`flex-1 transition-all duration-300 ${
            hasActiveOrder ? 'hidden md:block md:w-3/5 lg:w-[62%]' : 'w-full md:w-3/5 lg:w-[62%]'
          }`}
        >
          <OrderGrid
            onSelectOrder={drawer.selectOrder}
            selectedOrderId={drawer.selectedOrderId}
            readyItems={readyItems}
            onDismissReadyItem={dismissReadyItem}
            onNewOrder={drawer.openNewOrderDrawer}
            onActiveOrdersCount={setActiveOrdersCount}
            refreshKey={refreshKey}
          />
        </div>

        {hasActiveOrder ? (
          <div className="w-full fixed inset-0 z-40 md:relative md:inset-auto md:w-2/5 lg:w-[38%] h-[calc(100vh-4rem)] md:h-[calc(100vh-7rem)]">
            <OrderDrawer
              order={drawer.activeOrder}
              draft={drawer.draft}
              activeMenu={drawer.activeMenu}
              isLoading={drawer.isLoading}
              isSubmitting={drawer.isSubmitting}
              isRequestingPayment={drawer.isRequestingPayment}
              isProcessingPayment={drawer.isProcessingPayment}
              isCancelling={drawer.isCancelling}
              isDelivering={drawer.isDelivering}
              onClose={drawer.closeDrawer}
              onCreateOrder={drawer.createOrder}
              onSelectItem={drawer.handleSelectItem}
              onUpdateDraftQuantity={drawer.updateDraftQuantity}
              onUpdateDraftNotes={drawer.updateDraftNotes}
              onSendToKitchen={drawer.sendToKitchen}
              onRequestPayment={drawer.requestPayment}
              onProcessPayment={drawer.processPayment}
              onDeliverOrder={drawer.deliverOrder}
              onCancelOrder={drawer.cancelOrder}
            />
          </div>
        ) : (
          <div className="hidden md:flex md:w-2/5 lg:w-[38%] flex-col gap-4 border border-gray-900/60 rounded-2xl bg-gray-950/10 p-5 backdrop-blur-md glass-card h-[calc(100vh-7rem)] overflow-y-auto">
            <div className="border-b border-gray-900 pb-3">
              <h3 className="text-xs font-black text-gray-400 uppercase tracking-widest">
                Painel Informativo
              </h3>
              <p className="text-[10px] text-gray-500 font-medium mt-0.5">
                Selecione uma comanda para ver os detalhes
              </p>
            </div>

            <div className="space-y-3 flex-1">
              <div className="flex items-center gap-2 text-brand-400 border border-brand-500/10 bg-brand-500/5 p-3.5 rounded-xl">
                <Coffee className="h-5 w-5 flex-shrink-0" />
                <div>
                  <h4 className="text-xs font-bold text-gray-200">Pronto para Atendimento</h4>
                  <p className="text-[10px] text-gray-400 mt-0.5">
                    O cardápio dinâmico foi carregado do backend.
                  </p>
                </div>
              </div>

              <div className="space-y-2">
                <h4 className="text-[10px] font-extrabold uppercase tracking-wider text-gray-500 flex items-center gap-1.5">
                  <BellRing className="h-3.5 w-3.5 text-rose-500" />
                  <span>Alertas Recentes da Cozinha ({readyItems.length})</span>
                </h4>
                {readyItems.length === 0 ? (
                  <div className="text-[10px] text-gray-500 italic p-3 rounded-xl border border-gray-900 bg-gray-900/20 text-center">
                    Nenhum prato pronto aguardando entrega.
                  </div>
                ) : (
                  <div className="space-y-2 max-h-[250px] overflow-y-auto pr-1">
                    {readyItems.map((item) => (
                      <div
                        key={item.id}
                        className="flex items-center justify-between p-3 rounded-xl border border-rose-500/20 bg-rose-500/5 hover:bg-rose-500/10 transition"
                      >
                        <div>
                          <h5 className="text-xs font-bold text-gray-200">{item.name_cpy}</h5>
                          <span className="text-[9px] uppercase font-bold text-gray-400 bg-white/[0.03] border border-gray-800 px-1.5 py-0.5 rounded mt-1 inline-block">
                            Estação: {item.station_type_cpy}
                          </span>
                        </div>
                        <button
                          type="button"
                          onClick={() => dismissReadyItem(item.id)}
                          className="rounded-lg bg-rose-500 hover:bg-rose-600 active:scale-95 text-white font-bold text-[9px] px-2.5 py-1.5 transition"
                        >
                          Entregue
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="border-t border-gray-900 pt-4 space-y-3">
              <div className="flex justify-between items-center text-xs">
                <span className="text-gray-400 font-medium">Comandas Ativas</span>
                <span className="text-white font-bold">
                  {activeOrdersCount} Aberta{activeOrdersCount !== 1 ? 's' : ''}
                </span>
              </div>
              <div className="flex justify-between items-center text-xs">
                <span className="text-gray-400 font-medium">Alertas Cozinha Pendentes</span>
                <span className="text-rose-400 font-bold">{readyItems.length} Pratos</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  )
}
