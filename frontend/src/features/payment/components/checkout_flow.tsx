import {
  ArrowLeft,
  ArrowRight,
  Calculator,
  CheckCircle,
  CreditCard,
  QrCode,
  Wallet,
} from 'lucide-react'
import { useState } from 'react'
import { httpClient } from '@/shared/lib/http_client'

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
  items: OrderItem[]
}

interface CheckoutFlowProps {
  tableNumber: number
  order: OrderForm
  onBack: () => void
  onPaymentCompleted: () => void
}

function BillingSummaryList({ items }: { items: OrderItem[] }) {
  return (
    <div className="max-h-[350px] overflow-y-auto space-y-3 pr-1">
      {items.map((item) => (
        <div
          key={item.id}
          className="flex items-start justify-between text-xs border-b border-gray-900 pb-2"
        >
          <div>
            <h4 className="font-semibold text-gray-200">{item.name_cpy}</h4>
            <span className="text-[10px] text-gray-500">
              R$ {Number(item.price_cpy).toFixed(2)} x {item.quantity}
            </span>
          </div>
          <span className="font-semibold text-gray-300">R$ {Number(item.subtotal).toFixed(2)}</span>
        </div>
      ))}
    </div>
  )
}

function PixForm() {
  return (
    <div className="flex flex-col items-center justify-center p-4 border border-gray-850 bg-gray-950/40 rounded-xl space-y-4">
      <div className="bg-white p-3 rounded-lg flex items-center justify-center">
        <svg className="w-32 h-32 text-black" viewBox="0 0 100 100">
          <title>Pix QR Code Mockup</title>
          <rect x="10" y="10" width="20" height="20" fill="currentColor" />
          <rect x="70" y="10" width="20" height="20" fill="currentColor" />
          <rect x="10" y="70" width="20" height="20" fill="currentColor" />
          <rect x="15" y="15" width="10" height="10" fill="white" />
          <rect x="75" y="15" width="10" height="10" fill="white" />
          <rect x="15" y="75" width="10" height="10" fill="white" />
          <circle cx="50" cy="50" r="12" fill="currentColor" />
          <rect x="40" y="20" width="8" height="8" fill="currentColor" />
          <rect x="25" y="45" width="15" height="10" fill="currentColor" />
          <rect x="55" y="65" width="20" height="12" fill="currentColor" />
        </svg>
      </div>
      <div className="w-full text-center space-y-1">
        <p className="text-[11px] text-gray-400 font-medium">Escaneie o QR Code Pix para pagar</p>
        <input
          type="text"
          readOnly
          value="00020101021226830014br.gov.bcb.pix2561comandafacil-pix-key-franquia-active-12345"
          className="w-full rounded border border-gray-850 bg-gray-950 px-2 py-1.5 text-center text-[10px] text-gray-500 font-mono focus:outline-none"
        />
      </div>
    </div>
  )
}

interface CardFormProps {
  holder: string
  number: string
  expiry: string
  cvv: string
  onChangeHolder: (val: string) => void
  onChangeNumber: (val: string) => void
  onChangeExpiry: (val: string) => void
  onChangeCvv: (val: string) => void
}

function CardForm({
  holder,
  number,
  expiry,
  cvv,
  onChangeHolder,
  onChangeNumber,
  onChangeExpiry,
  onChangeCvv,
}: CardFormProps) {
  return (
    <div className="space-y-3 p-4 border border-gray-850 bg-gray-950/40 rounded-xl">
      <div className="grid gap-2">
        <input
          type="text"
          placeholder="Nome do Titular"
          value={holder}
          onChange={(e) => onChangeHolder(e.target.value)}
          className="w-full rounded border border-gray-850 bg-gray-950 px-3 py-2 text-xs text-white placeholder-gray-650 focus:border-brand-500 focus:outline-none"
        />
        <input
          type="text"
          placeholder="Número do Cartão"
          value={number}
          onChange={(e) => onChangeNumber(e.target.value)}
          className="w-full rounded border border-gray-850 bg-gray-950 px-3 py-2 text-xs text-white placeholder-gray-650 focus:border-brand-500 focus:outline-none"
        />
        <div className="grid grid-cols-2 gap-2">
          <input
            type="text"
            placeholder="Vencimento (MM/AA)"
            value={expiry}
            onChange={(e) => onChangeExpiry(e.target.value)}
            className="w-full rounded border border-gray-850 bg-gray-950 px-3 py-2 text-xs text-white placeholder-gray-650 focus:border-brand-500 focus:outline-none"
          />
          <input
            type="text"
            placeholder="CVV"
            value={cvv}
            onChange={(e) => onChangeCvv(e.target.value)}
            className="w-full rounded border border-gray-850 bg-gray-950 px-3 py-2 text-xs text-white placeholder-gray-650 focus:border-brand-500 focus:outline-none"
          />
        </div>
      </div>
    </div>
  )
}

interface CashFormProps {
  receivedAmount: string
  grandTotal: number
  onChangeReceived: (val: string) => void
}

function CashForm({ receivedAmount, grandTotal, onChangeReceived }: CashFormProps) {
  const cashReceived = Number(receivedAmount) || 0
  const cashChange = cashReceived > grandTotal ? cashReceived - grandTotal : 0

  return (
    <div className="space-y-3.5 p-4 border border-gray-850 bg-gray-950/40 rounded-xl">
      <div className="flex items-center gap-2">
        <Calculator className="h-4 w-4 text-brand-400" />
        <span className="text-xs font-semibold text-gray-300">Cálculo de Troco</span>
      </div>

      <div className="space-y-2">
        <label
          htmlFor="cash-input"
          className="block text-[10px] uppercase font-bold tracking-wider text-gray-500"
        >
          Valor Entregue pelo Cliente (R$)
        </label>
        <input
          id="cash-input"
          type="number"
          placeholder="Ex: 50.00"
          value={receivedAmount}
          onChange={(e) => onChangeReceived(e.target.value)}
          className="w-full rounded border border-gray-850 bg-gray-950 px-3 py-2 text-sm font-semibold text-white placeholder-gray-650 focus:border-brand-500 focus:outline-none"
        />
      </div>

      <div className="border-t border-gray-900 pt-3 flex justify-between items-baseline">
        <span className="text-[11px] text-gray-400">Troco a devolver:</span>
        <span
          className={`text-base font-extrabold ${cashChange > 0 ? 'text-emerald-400' : 'text-gray-500'}`}
        >
          R$ {cashChange.toFixed(2)}
        </span>
      </div>
    </div>
  )
}

interface PaymentSuccessViewProps {
  grandTotal: number
  paymentMethod: string
  isClosingTable: boolean
  onCloseTable: () => void
}

function PaymentSuccessView({
  grandTotal,
  paymentMethod,
  isClosingTable,
  onCloseTable,
}: PaymentSuccessViewProps) {
  return (
    <div className="max-w-md mx-auto rounded-2xl border border-emerald-500/20 bg-emerald-950/5 p-8 text-center backdrop-blur-md space-y-6">
      <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
        <CheckCircle className="h-10 w-10 animate-bounce" />
      </div>
      <div className="space-y-2">
        <h3 className="text-lg font-bold text-white">Comanda Paga!</h3>
        <p className="text-xs text-gray-400">
          O pagamento foi concluído e registrado. Agora você pode fechar e liberar a mesa.
        </p>
      </div>

      <div className="rounded-xl border border-gray-850 bg-gray-900/40 p-4 space-y-2 text-xs">
        <div className="flex justify-between">
          <span className="text-gray-400">Total Pago</span>
          <span className="font-bold text-white">R$ {grandTotal.toFixed(2)}</span>
        </div>
        <div className="flex justify-between border-t border-gray-800 pt-2 text-gray-400">
          <span>Método</span>
          <span className="font-semibold">
            {paymentMethod === 'PIX' ? 'Pix' : paymentMethod === 'CARD' ? 'Cartão' : 'Dinheiro'}
          </span>
        </div>
      </div>

      <button
        type="button"
        disabled={isClosingTable}
        onClick={onCloseTable}
        className="flex w-full items-center justify-center gap-2 rounded-lg bg-emerald-500 hover:bg-emerald-600 active:scale-[0.98] py-3 text-sm font-bold text-white transition duration-200"
      >
        {isClosingTable ? (
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent" />
        ) : (
          <>
            Liberar Mesa
            <ArrowRight className="h-4 w-4" />
          </>
        )}
      </button>
    </div>
  )
}

export default function CheckoutFlow({
  tableNumber,
  order,
  onBack,
  onPaymentCompleted,
}: CheckoutFlowProps) {
  const [paymentMethod, setPaymentMethod] = useState<'CASH' | 'CARD' | 'PIX'>('PIX')
  const [isProcessing, setIsProcessing] = useState(false)
  const [isClosingTable, setIsClosingTable] = useState(false)
  const [paymentSuccess, setPaymentSuccess] = useState(order.state === 'PAID')

  const [receivedAmount, setReceivedAmount] = useState('')
  const [cardNumber, setCardNumber] = useState('')
  const [cardHolder, setCardHolder] = useState('')
  const [cardExpiry, setCardExpiry] = useState('')
  const [cardCvv, setCardCvv] = useState('')

  const subtotal = Number(order.total)
  const serviceCharge = subtotal * 0.1
  const grandTotal = subtotal + serviceCharge

  const handleProcessPayment = async () => {
    setIsProcessing(true)
    try {
      await httpClient.post(`/v1/order/${order.id}/process-payment`)
      setPaymentSuccess(true)
      alert('Pagamento processado e registrado com sucesso!')
    } catch (_err) {
      alert('Falha ao processar pagamento. Tente novamente.')
    } finally {
      setIsProcessing(false)
    }
  }

  const handleCloseAndDeliver = async () => {
    setIsClosingTable(true)
    try {
      await httpClient.post(`/v1/order/${order.id}/deliver`)
      alert('Mesa fechada e liberada com sucesso!')
      onPaymentCompleted()
    } catch (_err) {
      alert('Erro ao arquivar e fechar a mesa no sistema.')
    } finally {
      setIsClosingTable(false)
    }
  }

  if (paymentSuccess) {
    return (
      <PaymentSuccessView
        grandTotal={grandTotal}
        paymentMethod={paymentMethod}
        isClosingTable={isClosingTable}
        onCloseTable={handleCloseAndDeliver}
      />
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3 border-b border-gray-800/80 pb-4">
        <button
          type="button"
          onClick={onBack}
          className="rounded-lg bg-gray-900 border border-gray-800 hover:border-gray-700 p-2 text-gray-400 hover:text-white transition"
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div>
          <h2 className="text-xl font-bold text-gray-100">Fechamento de Conta</h2>
          <p className="text-xs text-gray-400">
            Mesa {tableNumber < 10 ? `0${tableNumber}` : tableNumber} — ID Comanda #{order.id}
          </p>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <div className="rounded-xl border border-gray-800/80 bg-gray-900/20 p-5 space-y-4">
          <h3 className="text-sm font-bold uppercase tracking-wider text-gray-400 border-b border-gray-850 pb-3">
            Resumo do Consumo
          </h3>
          <BillingSummaryList items={order.items} />
          <div className="border-t border-gray-800/80 pt-4 space-y-2 text-xs">
            <div className="flex justify-between text-gray-400">
              <span>Subtotal Consumido</span>
              <span>R$ {subtotal.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-gray-400">
              <span>Taxa de Serviço (10%)</span>
              <span>R$ {serviceCharge.toFixed(2)}</span>
            </div>
            <div className="flex justify-between border-t border-gray-850 pt-3 text-sm font-extrabold text-white">
              <span>Total Geral</span>
              <span className="text-amber-500 text-lg">R$ {grandTotal.toFixed(2)}</span>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-gray-800/80 bg-gray-900/20 p-5 flex flex-col justify-between">
          <div className="space-y-4">
            <h3 className="text-sm font-bold uppercase tracking-wider text-gray-400 border-b border-gray-850 pb-3">
              Forma de Pagamento
            </h3>

            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => setPaymentMethod('PIX')}
                className={`flex flex-col items-center justify-center gap-1.5 rounded-lg border py-3 text-xs font-semibold transition ${
                  paymentMethod === 'PIX'
                    ? 'border-brand-500/50 bg-brand-950/15 text-brand-400'
                    : 'border-gray-800 bg-gray-900/40 text-gray-400 hover:text-white'
                }`}
              >
                <QrCode className="h-4 w-4" />
                Pix
              </button>
              <button
                type="button"
                onClick={() => setPaymentMethod('CARD')}
                className={`flex flex-col items-center justify-center gap-1.5 rounded-lg border py-3 text-xs font-semibold transition ${
                  paymentMethod === 'CARD'
                    ? 'border-brand-500/50 bg-brand-950/15 text-brand-400'
                    : 'border-gray-800 bg-gray-900/40 text-gray-400 hover:text-white'
                }`}
              >
                <CreditCard className="h-4 w-4" />
                Cartão
              </button>
              <button
                type="button"
                onClick={() => setPaymentMethod('CASH')}
                className={`flex flex-col items-center justify-center gap-1.5 rounded-lg border py-3 text-xs font-semibold transition ${
                  paymentMethod === 'CASH'
                    ? 'border-brand-500/50 bg-brand-950/15 text-brand-400'
                    : 'border-gray-800 bg-gray-900/40 text-gray-400 hover:text-white'
                }`}
              >
                <Wallet className="h-4 w-4" />
                Dinheiro
              </button>
            </div>

            <div className="pt-2">
              {paymentMethod === 'PIX' && <PixForm />}
              {paymentMethod === 'CARD' && (
                <CardForm
                  holder={cardHolder}
                  number={cardNumber}
                  expiry={cardExpiry}
                  cvv={cardCvv}
                  onChangeHolder={setCardHolder}
                  onChangeNumber={setCardNumber}
                  onChangeExpiry={setCardExpiry}
                  onChangeCvv={setCardCvv}
                />
              )}
              {paymentMethod === 'CASH' && (
                <CashForm
                  receivedAmount={receivedAmount}
                  grandTotal={grandTotal}
                  onChangeReceived={setReceivedAmount}
                />
              )}
            </div>
          </div>

          <button
            type="button"
            disabled={
              isProcessing || (paymentMethod === 'CASH' && Number(receivedAmount) < grandTotal)
            }
            onClick={handleProcessPayment}
            className="mt-6 flex w-full items-center justify-center gap-2 rounded-lg bg-brand-500 hover:bg-brand-600 active:scale-[0.98] py-3 text-sm font-bold text-white transition duration-200 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {isProcessing ? (
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent" />
            ) : (
              <>
                Processar e Confirmar
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
