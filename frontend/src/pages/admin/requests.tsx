import { AlertCircle, ArrowUpCircle, CheckCircle2, MessageSquare, XCircle } from 'lucide-react'
import type React from 'react'
import { useState } from 'react'

interface RequestTicket {
  id: number
  tenantName: string
  type: 'UPGRADE' | 'SUPORTE' | 'BILLING'
  description: string
  date: string
  status: 'PENDENTE' | 'APROVADO' | 'REJEITADO' | 'RESOLVIDO'
}

const INITIAL_TICKETS: RequestTicket[] = [
  {
    id: 1,
    tenantName: 'Barraca do Sol',
    type: 'UPGRADE',
    description: 'Solicitação de upgrade de plano: BASIC para PRO para habilitar múltiplas KDS.',
    date: 'Hoje, 10:24',
    status: 'PENDENTE',
  },
  {
    id: 2,
    tenantName: 'Quiosque Copacabana',
    type: 'SUPORTE',
    description: 'Dificuldade na integração de impressoras térmicas Bluetooth nas comandas.',
    date: 'Ontem, 16:45',
    status: 'PENDENTE',
  },
  {
    id: 3,
    tenantName: 'Lanchonete Express',
    type: 'BILLING',
    description: 'Ajuste cadastral de dados na nota de serviço consolidada do mês.',
    date: '2 dias atrás',
    status: 'PENDENTE',
  },
  {
    id: 4,
    tenantName: 'Restaurante Central',
    type: 'UPGRADE',
    description: 'Upgrade automático solicitado para plano PLUS (Faturamento Ilimitado).',
    date: '3 dias atrás',
    status: 'APROVADO',
  },
  {
    id: 5,
    tenantName: 'Beach Point Barra',
    type: 'SUPORTE',
    description: 'Suporte urgente: Erro de sincronização no painel financeiro histórico.',
    date: '4 dias atrás',
    status: 'RESOLVIDO',
  },
]

const RequestTicketCard: React.FC<{
  ticket: RequestTicket
  onUpdateStatus: (id: number, status: 'APROVADO' | 'REJEITADO' | 'RESOLVIDO') => void
}> = ({ ticket: t, onUpdateStatus }) => {
  return (
    <div className="bg-gray-950/40 border border-gray-900/60 rounded-2xl p-5 backdrop-blur-md flex flex-col md:flex-row md:items-center md:justify-between gap-4 shadow-lg hover:border-gray-800 transition-all">
      <div className="space-y-2 max-w-xl">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-extrabold text-white text-xs">{t.tenantName}</span>
          <span className="text-gray-600">•</span>
          <span className="text-[10px] text-gray-500 font-bold">{t.date}</span>
          <span className="text-gray-600">•</span>
          <span
            className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-lg border text-[9px] font-bold ${
              t.type === 'UPGRADE'
                ? 'bg-purple-500/10 border-purple-500/20 text-purple-400'
                : t.type === 'SUPORTE'
                  ? 'bg-amber-500/10 border-amber-500/20 text-amber-400'
                  : 'bg-blue-500/10 border-blue-500/20 text-blue-400'
            }`}
          >
            {t.type === 'UPGRADE' ? (
              <ArrowUpCircle className="h-3 w-3" />
            ) : t.type === 'SUPORTE' ? (
              <AlertCircle className="h-3 w-3" />
            ) : (
              <MessageSquare className="h-3 w-3" />
            )}
            {t.type}
          </span>
        </div>
        <p className="text-xs font-medium text-gray-300 leading-relaxed">{t.description}</p>
      </div>

      {/* Status badge & Actions */}
      <div className="flex items-center gap-3 self-end md:self-center">
        {t.status === 'PENDENTE' ? (
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => onUpdateStatus(t.id, t.type === 'UPGRADE' ? 'APROVADO' : 'RESOLVIDO')}
              className="flex items-center justify-center gap-1 bg-green-500/10 hover:bg-green-500/20 border border-green-500/30 hover:border-green-500/40 text-green-400 px-3.5 py-2 rounded-xl text-[10px] font-bold transition-all"
            >
              <CheckCircle2 className="h-3.5 w-3.5" />
              {t.type === 'UPGRADE' ? 'Aprovar Upgrade' : 'Marcar como Resolvido'}
            </button>
            <button
              type="button"
              onClick={() => onUpdateStatus(t.id, 'REJEITADO')}
              className="flex items-center justify-center gap-1 bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 hover:border-red-500/40 text-red-400 px-3.5 py-2 rounded-xl text-[10px] font-bold transition-all"
            >
              <XCircle className="h-3.5 w-3.5" />
              Rejeitar
            </button>
          </div>
        ) : (
          <span
            className={`inline-flex items-center gap-1 px-3 py-1 rounded-xl text-[10px] font-bold border ${
              t.status === 'APROVADO' || t.status === 'RESOLVIDO'
                ? 'bg-green-500/10 border-green-500/20 text-green-400'
                : 'bg-red-500/10 border-red-500/20 text-red-400'
            }`}
          >
            {t.status === 'APROVADO' || t.status === 'RESOLVIDO' ? (
              <CheckCircle2 className="h-3.5 w-3.5" />
            ) : (
              <XCircle className="h-3.5 w-3.5" />
            )}
            {t.status}
          </span>
        )}
      </div>
    </div>
  )
}

export const AdminRequestsPage: React.FC = () => {
  const [tickets, setTickets] = useState<RequestTicket[]>(INITIAL_TICKETS)

  const handleUpdateStatus = (id: number, newStatus: 'APROVADO' | 'REJEITADO' | 'RESOLVIDO') => {
    setTickets(tickets.map((t) => (t.id === id ? { ...t, status: newStatus } : t)))
  }

  return (
    <div className="space-y-6">
      {/* Title */}
      <div>
        <h1 className="text-2xl font-black tracking-tight text-white">Solicitações Pendentes</h1>
        <p className="text-xs font-medium text-gray-400 mt-1">
          Gerencie solicitações de licenças, upgrades e chamados de suporte técnico enviados pelas
          unidades.
        </p>
      </div>

      {/* Ticket List */}
      <div className="space-y-4">
        {tickets.map((t) => (
          <RequestTicketCard key={t.id} ticket={t} onUpdateStatus={handleUpdateStatus} />
        ))}
      </div>
    </div>
  )
}
