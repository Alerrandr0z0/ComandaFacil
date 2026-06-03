import { BellRing, Coffee, Settings } from 'lucide-react'
import { useState } from 'react'
import { useAuth } from '@/features/auth/auth_context'
import OrderDrawer from '@/features/order/components/order_drawer'
import TableGrid from '@/features/order/components/table_grid'
import { useKitchenAlerts } from '@/features/order/hooks/use_kitchen_alerts'
import { useOrderDrawer } from '@/features/order/hooks/use_order_drawer'
import Layout from '@/shared/components/layout'

export default function OrdersPage() {
  const { employee } = useAuth()
  const drawer = useOrderDrawer()
  const { readyItems, dismissReadyItem } = useKitchenAlerts()
  const [isConfigOpen, setIsConfigOpen] = useState(false)
  const [tablesInput, setTablesInput] = useState(localStorage.getItem('cf_tables_count') || '12')

  const isManager = employee?.role === 'MANAGER'

  const handleSaveTablesCount = (e: React.FormEvent) => {
    e.preventDefault()
    const num = parseInt(tablesInput, 10)
    if (!Number.isNaN(num) && num > 0 && num <= 100) {
      localStorage.setItem('cf_tables_count', num.toString())
      setIsConfigOpen(false)
      window.location.reload() // Reload to reset table grid counts
    } else {
      alert('Por favor, digite um número entre 1 e 100.')
    }
  }

  // Count active tables in the system (from the drawer active state or local status)
  const tablesCount = parseInt(tablesInput, 10) || 12

  return (
    <Layout>
      <div className="flex h-full gap-6 relative">
        {/* Left Side: Table Grid (100% on mobile, 60% on desktop/tablet) */}
        <div
          className={`flex-1 transition-all duration-300 ${
            drawer.selectedTableNumber !== null ? 'hidden md:block md:w-3/5 lg:w-[62%]' : 'w-full'
          }`}
        >
          {/* Header toolbar */}
          {isManager && (
            <div className="flex items-center justify-end mb-4 gap-2">
              <button
                type="button"
                onClick={() => setIsConfigOpen(!isConfigOpen)}
                className="rounded-xl bg-gray-900/30 border border-gray-850 hover:border-gray-700 px-3 py-2 text-xs font-bold text-gray-400 hover:text-white transition flex items-center gap-1.5"
              >
                <Settings className="h-3.5 w-3.5" />
                <span>Configurar Salão</span>
              </button>
            </div>
          )}

          {/* Salon Tables Configuration Modal */}
          {isConfigOpen && isManager && (
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
              <form
                onSubmit={handleSaveTablesCount}
                className="w-full max-w-sm rounded-2xl glass-elevated p-6 space-y-4"
              >
                <div>
                  <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                    Configurar Grid do Salão
                  </h3>
                  <p className="text-xs text-gray-500 mt-1">
                    Defina o número de mesas visíveis no painel
                  </p>
                </div>
                <div className="space-y-1.5">
                  <span className="block text-[10px] uppercase font-extrabold text-gray-400">
                    Quantidade de Mesas
                  </span>
                  <input
                    type="number"
                    min="1"
                    max="100"
                    value={tablesInput}
                    onChange={(e) => setTablesInput(e.target.value)}
                    className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input"
                  />
                </div>
                <div className="flex gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setIsConfigOpen(false)}
                    className="flex-1 rounded-xl border border-gray-850 hover:bg-white/[0.02] py-2.5 text-xs font-bold text-gray-400 transition"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    className="flex-1 rounded-xl bg-brand-500 hover:bg-brand-600 py-2.5 text-xs font-bold text-white transition"
                  >
                    Salvar Mudanças
                  </button>
                </div>
              </form>
            </div>
          )}

          <TableGrid
            onSelectTable={drawer.selectTable}
            selectedTableNumber={drawer.selectedTableNumber}
            readyItems={readyItems}
            onDismissReadyItem={dismissReadyItem}
          />
        </div>

        {/* Right Side: Order Drawer (Full screen overlay on mobile, 40% side view on desktop) */}
        {drawer.selectedTableNumber !== null ? (
          <div className="w-full fixed inset-0 z-40 md:relative md:inset-auto md:w-2/5 lg:w-[38%] h-[calc(100vh-4rem)] md:h-[calc(100vh-7rem)]">
            <OrderDrawer
              tableNumber={drawer.selectedTableNumber}
              activeOrder={drawer.activeOrder}
              draft={drawer.draft}
              activeMenu={drawer.activeMenu}
              isLoading={drawer.isLoading}
              isSubmitting={drawer.isSubmitting}
              isRequestingPayment={drawer.isRequestingPayment}
              isProcessingPayment={drawer.isProcessingPayment}
              isCancelling={drawer.isCancelling}
              isDelivering={drawer.isDelivering}
              onClose={drawer.closeDrawer}
              onOpenTable={() => drawer.openTable(drawer.selectedTableNumber ?? 0)}
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
          /* Empty side view - show metrics and alerts */
          <div className="hidden md:flex md:w-2/5 lg:w-[38%] flex-col gap-4 border border-gray-900/60 rounded-2xl bg-gray-950/10 p-5 backdrop-blur-md glass-card h-[calc(100vh-7rem)] overflow-y-auto">
            <div className="border-b border-gray-900 pb-3">
              <h3 className="text-xs font-black text-gray-400 uppercase tracking-widest">
                Painel Informativo
              </h3>
              <p className="text-[10px] text-gray-500 font-medium mt-0.5">
                Selecione uma mesa para ver os detalhes
              </p>
            </div>

            {/* Alert List */}
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

            {/* Quick overview of salon status */}
            <div className="border-t border-gray-900 pt-4 space-y-3">
              <div className="flex justify-between items-center text-xs">
                <span className="text-gray-400 font-medium">Capacidade do Salão</span>
                <span className="text-white font-bold">{tablesCount} Mesas</span>
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
