import { Check, X } from 'lucide-react'
import { useEffect, useState } from 'react'

interface PaymentModalProps {
  isOpen: boolean
  onClose: () => void
  total: number
  onConfirm: (
    method: 'PIX' | 'CREDIT' | 'DEBIT' | 'CASH',
    receivedAmount?: number,
  ) => Promise<unknown>
}

type PaymentMethod = 'PIX' | 'CREDIT' | 'DEBIT' | 'CASH'

export default function PaymentModal({ isOpen, onClose, total, onConfirm }: PaymentModalProps) {
  const [selectedMethod, setSelectedMethod] = useState<PaymentMethod | null>(null)
  const [receivedAmount, setReceivedAmount] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [change, setChange] = useState<number | null>(null)

  useEffect(() => {
    if (isOpen) {
      setSelectedMethod(null)
      setReceivedAmount('')
      setChange(null)
      setIsLoading(false)
    }
  }, [isOpen])

  // Calculate change for cash payment
  useEffect(() => {
    if (selectedMethod === 'CASH' && receivedAmount) {
      const received = parseFloat(receivedAmount)
      if (!Number.isNaN(received) && received >= total) {
        setChange(received - total)
      } else {
        setChange(null)
      }
    } else {
      setChange(null)
    }
  }, [selectedMethod, receivedAmount, total])

  if (!isOpen) return null

  const handleSelectMethod = (method: PaymentMethod) => {
    setSelectedMethod(method)
    if (method !== 'CASH') {
      setReceivedAmount('')
    }
  }

  const handleQuickAmount = (amount: number) => {
    setReceivedAmount(amount.toFixed(2))
  }

  const handleConfirm = async () => {
    if (!selectedMethod) return

    let received: number | undefined
    if (selectedMethod === 'CASH') {
      received = parseFloat(receivedAmount)
      if (Number.isNaN(received) || received < total) {
        alert('Por favor, insira um valor válido igual ou maior que o total.')
        return
      }
    }

    setIsLoading(true)
    try {
      await onConfirm(selectedMethod, received)
      onClose()
    } catch (_error) {
      alert('Falha ao processar pagamento. Tente novamente.')
    } finally {
      setIsLoading(false)
    }
  }

  // Pre-calculate shortcut cash options
  const shortcutValues = [
    total,
    Math.ceil(total / 10) * 10,
    Math.ceil(total / 50) * 50 || 50,
    Math.ceil(total / 100) * 100 || 100,
  ].filter((v, i, self) => self.indexOf(v) === i && v >= total)

  return (
    <div className="fixed inset-0 z-55 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md animate-fade-in">
      <div className="w-full max-w-lg rounded-2xl glass-elevated overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-900/60 p-4">
          <div>
            <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider">
              Registrar Pagamento
            </h3>
            <p className="text-xs text-gray-500 mt-0.5">
              Selecione a forma de pagamento do cliente
            </p>
          </div>
          <button
            type="button"
            disabled={isLoading}
            onClick={onClose}
            className="rounded-lg p-1.5 text-gray-500 hover:text-gray-200 transition bg-white/[0.03]"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 space-y-6">
          {/* Total Display */}
          <div className="flex flex-col items-center justify-center rounded-2xl bg-brand-500/5 border border-brand-500/10 py-5">
            <span className="text-[10px] uppercase font-extrabold tracking-widest text-brand-400">
              Total a Pagar
            </span>
            <span className="text-3xl font-black text-white mt-1">R$ {total.toFixed(2)}</span>
          </div>

          {/* Payment Methods Grid */}
          <div className="space-y-2.5">
            <span className="block text-[10px] uppercase tracking-wider font-extrabold text-brand-400">
              Meio de Pagamento
            </span>
            <div className="grid grid-cols-2 gap-3">
              {[
                { id: 'PIX', label: 'PIX (Código QR)' },
                { id: 'CREDIT', label: 'Cartão de Crédito' },
                { id: 'DEBIT', label: 'Cartão de Débito' },
                { id: 'CASH', label: 'Dinheiro (Espécie)' },
              ].map((m) => {
                const isSelected = selectedMethod === m.id
                return (
                  <button
                    type="button"
                    key={m.id}
                    onClick={() => handleSelectMethod(m.id as PaymentMethod)}
                    className={`flex items-center justify-between rounded-xl px-4 py-3.5 text-xs font-bold border transition-all duration-300 ${
                      isSelected
                        ? 'bg-brand-500/10 border-brand-500/30 text-brand-400 shadow-md shadow-brand-500/5'
                        : 'border-gray-850 bg-gray-900/10 text-gray-400 hover:text-white hover:border-gray-800'
                    }`}
                  >
                    <span>{m.label}</span>
                    {isSelected && <Check className="h-4 w-4 text-brand-400" />}
                  </button>
                )
              })}
            </div>
          </div>

          {/* Cash Details Panel */}
          {selectedMethod === 'CASH' && (
            <div className="rounded-2xl border border-gray-850 bg-gray-900/10 p-4 space-y-4 animate-fade-in">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <span className="block text-[10px] uppercase font-extrabold text-gray-500">
                    Valor Recebido
                  </span>
                  <div className="relative">
                    <span className="absolute inset-y-0 left-0 flex items-center pl-3.5 text-xs font-bold text-gray-500">
                      R$
                    </span>
                    <input
                      type="number"
                      step="0.01"
                      value={receivedAmount}
                      onChange={(e) => setReceivedAmount(e.target.value)}
                      placeholder="0,00"
                      className="w-full rounded-xl pl-9 pr-4 py-3 text-sm text-white glass-input"
                    />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <span className="block text-[10px] uppercase font-extrabold text-gray-500">
                    Troco
                  </span>
                  <div
                    className={`w-full rounded-xl py-3 px-4 text-sm font-black border flex items-center justify-between h-11 ${
                      change !== null
                        ? 'bg-emerald-500/5 border-emerald-500/20 text-emerald-400'
                        : 'bg-gray-900/20 border-gray-850 text-gray-500'
                    }`}
                  >
                    <span>R$</span>
                    <span>{change !== null ? change.toFixed(2) : '0,00'}</span>
                  </div>
                </div>
              </div>

              {/* Shortcut helpers */}
              <div className="space-y-1.5">
                <span className="block text-[9px] uppercase font-extrabold text-gray-500">
                  Valores Rápidos
                </span>
                <div className="flex gap-2">
                  {shortcutValues.map((val) => (
                    <button
                      type="button"
                      key={val}
                      onClick={() => handleQuickAmount(val)}
                      className="flex-1 py-1.5 px-3 rounded-lg border border-gray-800 bg-gray-900/40 text-[10px] font-bold text-gray-400 hover:text-white hover:border-gray-700 transition"
                    >
                      R$ {val.toFixed(2)}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex border-t border-gray-900/60 p-4 gap-3 bg-gray-950/20">
          <button
            type="button"
            disabled={isLoading}
            onClick={onClose}
            className="flex-1 rounded-xl border border-gray-800 hover:bg-white/[0.02] py-3 text-xs font-bold text-gray-400 hover:text-white transition duration-200"
          >
            Cancelar
          </button>
          <button
            type="button"
            disabled={
              isLoading || !selectedMethod || (selectedMethod === 'CASH' && change === null)
            }
            onClick={handleConfirm}
            className="flex-grow flex items-center justify-center gap-1.5 rounded-xl bg-brand-500 hover:bg-brand-600 disabled:bg-gray-800 disabled:text-gray-500 disabled:border-transparent active:scale-[0.98] py-3 text-xs font-bold text-white transition duration-200 shadow-lg"
          >
            {isLoading ? (
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
            ) : (
              <>
                <Check className="h-4 w-4" />
                Confirmar Pagamento
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
