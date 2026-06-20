import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Building, Key, Mail, Plus, Shield, Trash2 } from 'lucide-react'
import type React from 'react'
import { useState } from 'react'
import {
  createManager,
  deleteManager,
  getManagers,
  getTenants,
  type Manager,
  type Tenant,
} from '@/features/admin/adminService'

interface ApiError {
  response?: {
    data?: {
      detail?: string
    }
  }
}

export const AdminManagersPage: React.FC = () => {
  const queryClient = useQueryClient()
  const { data: managers, isLoading: loadingManagers } = useQuery({
    queryKey: ['managers'],
    queryFn: getManagers,
  })
  const { data: tenants, isLoading: loadingTenants } = useQuery({
    queryKey: ['tenants'],
    queryFn: getTenants,
  })

  const [showAddModal, setShowAddModal] = useState(false)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [selectedTenantId, setSelectedTenantId] = useState<number | ''>('')

  const createMutation = useMutation({
    mutationFn: createManager,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['managers'] })
      setName('')
      setEmail('')
      setPassword('')
      setSelectedTenantId('')
      setShowAddModal(false)
    },
    onError: (err: ApiError) => {
      alert(err.response?.data?.detail || 'Erro ao registrar gerente')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteManager,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['managers'] })
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim() || !email.trim() || !password.trim() || selectedTenantId === '') return
    createMutation.mutate({
      name,
      email,
      password,
      tenant_id: Number(selectedTenantId),
    })
  }

  const getTenantName = (id: number) => {
    if (!Array.isArray(tenants)) return `Franquia #${id}`
    const tenant = tenants.find((t: Tenant) => t.id === id)
    return tenant ? tenant.name : `Franquia #${id}`
  }

  if (loadingManagers || loadingTenants) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-500 border-t-transparent" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Title & Add button */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black tracking-tight text-white">Gerentes de Franquia</h1>
          <p className="text-xs font-medium text-gray-400 mt-1">
            Cadastre credenciais administrativas e associe gerentes às respectivas unidades.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowAddModal(true)}
          className="flex items-center justify-center gap-2 bg-brand-500 hover:bg-brand-600 px-4 py-2.5 rounded-xl text-xs font-bold text-white shadow-lg shadow-brand-500/20 transition-all sm:self-center"
        >
          <Plus className="h-4 w-4" />
          Novo Gerente
        </button>
      </div>

      {/* Managers Table */}
      <div className="bg-gray-950/40 border border-gray-900/60 rounded-2xl backdrop-blur-md overflow-hidden shadow-lg">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-gray-900/60 bg-gray-900/10 text-gray-400 text-[10px] font-bold uppercase tracking-wider">
                <th className="px-6 py-4">Nome</th>
                <th className="px-6 py-4">E-mail</th>
                <th className="px-6 py-4">Franquia Associada</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4 text-right">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-900/40 text-xs font-medium text-gray-300">
              {Array.isArray(managers) && managers.length > 0 ? (
                managers.map((m: Manager) => (
                  <tr key={m.id} className="hover:bg-white/[0.01] transition-all">
                    <td className="px-6 py-4 font-bold text-white">
                      <div className="flex items-center gap-2">
                        <Shield className="h-3.5 w-3.5 text-brand-400" />
                        <span>{m.name}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-gray-400">{m.email}</td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2 text-brand-400">
                        <Building className="h-3.5 w-3.5 text-gray-500" />
                        <span className="font-bold">{getTenantName(m.tenant_id)}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                          m.is_active
                            ? 'bg-green-500/10 border-green-500/20 text-green-400'
                            : 'bg-red-500/10 border-red-500/20 text-red-400'
                        }`}
                      >
                        {m.is_active ? 'Ativo' : 'Suspenso'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button
                        type="button"
                        onClick={() => {
                          if (window.confirm(`Deseja revogar o cargo de gerente de "${m.name}"?`)) {
                            deleteMutation.mutate(m.id)
                          }
                        }}
                        className="text-red-400 hover:text-red-300 hover:bg-red-500/10 border border-transparent hover:border-red-500/20 p-2 rounded-xl transition-all"
                        title="Remover Gerente"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="px-6 py-8 text-center text-gray-500">
                    Nenhum gerente cadastrado.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-fade-in">
          <div className="bg-gray-950 border border-gray-900 rounded-2xl max-w-md w-full p-6 space-y-6 shadow-2xl">
            <div>
              <h3 className="text-lg font-black text-white">Cadastrar Novo Gerente</h3>
              <p className="text-xs text-gray-400 mt-1">
                Crie a credencial de acesso do gerente para uma franquia específica.
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <label
                  htmlFor="mgrName"
                  className="text-xs font-bold text-gray-400 uppercase tracking-wider"
                >
                  Nome Completo
                </label>
                <input
                  id="mgrName"
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Nome do gerente"
                  className="w-full bg-gray-900 border border-gray-800 rounded-xl px-4 py-3 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-brand-500 transition-all"
                />
              </div>

              <div className="space-y-1.5">
                <label
                  htmlFor="mgrEmail"
                  className="text-xs font-bold text-gray-400 uppercase tracking-wider"
                >
                  E-mail Corporativo
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
                  <input
                    id="mgrEmail"
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="email@comanda.com"
                    className="w-full bg-gray-900 border border-gray-800 rounded-xl pl-10 pr-4 py-3 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-brand-500 transition-all"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label
                  htmlFor="mgrPass"
                  className="text-xs font-bold text-gray-400 uppercase tracking-wider"
                >
                  Senha Provisória
                </label>
                <div className="relative">
                  <Key className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
                  <input
                    id="mgrPass"
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Mínimo 6 caracteres"
                    className="w-full bg-gray-900 border border-gray-800 rounded-xl pl-10 pr-4 py-3 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-brand-500 transition-all"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label
                  htmlFor="mgrTenant"
                  className="text-xs font-bold text-gray-400 uppercase tracking-wider"
                >
                  Franquia Vinculada
                </label>
                <select
                  id="mgrTenant"
                  required
                  value={selectedTenantId}
                  onChange={(e) =>
                    setSelectedTenantId(e.target.value ? Number(e.target.value) : '')
                  }
                  className="w-full bg-gray-900 border border-gray-800 rounded-xl px-4 py-3 text-xs text-white focus:outline-none focus:border-brand-500 transition-all"
                >
                  <option value="">Selecione uma Franquia...</option>
                  {Array.isArray(tenants) &&
                    tenants.map((t: Tenant) => (
                      <option key={t.id} value={t.id}>
                        {t.name} (ID: #{t.id})
                      </option>
                    ))}
                </select>
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="bg-gray-900 hover:bg-gray-850 px-4 py-2.5 rounded-xl text-xs font-bold transition-all"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="bg-brand-500 hover:bg-brand-600 px-4 py-2.5 rounded-xl text-xs font-bold text-white shadow-lg shadow-brand-500/20 transition-all disabled:opacity-50"
                >
                  {createMutation.isPending ? 'Registrando...' : 'Registrar Gerente'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
