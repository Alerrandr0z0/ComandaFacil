import { Lock, Mail, Power, RefreshCcw, Shield, Trash, UserPlus, Users } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '@/features/auth/auth_context'
import Layout from '@/shared/components/layout'
import { useTenant } from '@/shared/hooks/useTenant'
import { httpClient } from '@/shared/lib/http_client'

interface Employee {
  id: number
  name: string
  email: string
  role: 'MANAGER' | 'WAITER' | 'COOK' | 'CASHIER' | null
  is_active: boolean
}

interface EmployeeCardProps {
  emp: Employee
  currentEmployee: { id: number } | null
  getRoleBadgeClasses: (role: string | null) => string
  formatRoleLabel: (role: string | null) => string
  onToggleActive: (emp: Employee) => void
  onDelete: (emp: Employee) => void
  onAssignRole: (emp: Employee) => void
}

function EmployeeCard({
  emp,
  currentEmployee,
  getRoleBadgeClasses,
  formatRoleLabel,
  onToggleActive,
  onDelete,
  onAssignRole,
}: EmployeeCardProps) {
  const isSelf = emp.id === currentEmployee?.id
  return (
    <div
      className={`p-5 rounded-2xl border border-gray-900 bg-gray-950/15 flex flex-col justify-between transition-all duration-300 hover:border-gray-800 ${
        isSelf ? 'border-brand-500/40 bg-brand-950/2' : ''
      }`}
    >
      <div>
        <div className="flex items-start justify-between">
          <div>
            <h4 className="text-xs font-bold text-gray-200">
              {emp.name}
              {isSelf && (
                <span className="text-[9px] text-brand-400 ml-1.5 font-normal">(Você)</span>
              )}
            </h4>
            <p className="text-[10px] text-gray-500 mt-0.5">ID: {emp.id}</p>
          </div>
          <div className="flex items-center gap-1.5">
            <span
              className={`text-[8px] px-1.5 py-0.5 rounded-full border uppercase tracking-wider font-extrabold ${
                emp.is_active
                  ? 'border-emerald-500/25 bg-emerald-500/10 text-emerald-400'
                  : 'border-rose-500/25 bg-rose-500/10 text-rose-450'
              }`}
            >
              {emp.is_active ? 'Ativo' : 'Suspenso'}
            </span>
            <span
              className={`text-[9px] px-2 py-0.5 rounded-full border uppercase tracking-wider font-extrabold ${getRoleBadgeClasses(
                emp.role,
              )}`}
            >
              {formatRoleLabel(emp.role)}
            </span>
          </div>
        </div>

        <div className="mt-4 space-y-1.5 text-xs text-gray-400">
          <div className="flex items-center gap-2">
            <Mail className="h-3.5 w-3.5 text-gray-600" />
            <span className="truncate">{emp.email}</span>
          </div>
        </div>
      </div>

      <div className="mt-5 pt-3.5 border-t border-gray-900/40 flex justify-between items-center">
        <div className="flex gap-1.5">
          {!isSelf && (
            <>
              <button
                type="button"
                onClick={() => onToggleActive(emp)}
                className={`p-1.5 rounded-lg border transition ${
                  emp.is_active
                    ? 'border-rose-500/20 bg-rose-950/10 text-rose-400 hover:bg-rose-500/20'
                    : 'border-emerald-500/20 bg-emerald-950/10 text-emerald-400 hover:bg-emerald-500/20'
                }`}
                title={emp.is_active ? 'Suspender Acesso' : 'Reativar Acesso'}
              >
                <Power className="h-3.5 w-3.5" />
              </button>
              <button
                type="button"
                onClick={() => onDelete(emp)}
                className="p-1.5 rounded-lg border border-red-500/20 bg-red-950/10 text-red-400 hover:bg-red-500/20 transition"
                title="Remover da Franquia"
              >
                <Trash className="h-3.5 w-3.5" />
              </button>
            </>
          )}
        </div>

        <button
          type="button"
          onClick={() => onAssignRole(emp)}
          className="rounded-lg bg-gray-900 border border-gray-850 hover:bg-gray-850 px-3 py-1.5 text-[10px] font-bold text-brand-400 hover:text-white transition flex items-center gap-1"
        >
          <Shield className="h-3 w-3" />
          Alterar Cargo
        </button>
      </div>
    </div>
  )
}

export default function EmployeesPage() {
  const { tenantId } = useTenant()
  const { employee: currentEmployee } = useAuth()

  const [employees, setEmployees] = useState<Employee[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isCreatingEmployee, setIsCreatingEmployee] = useState(false)
  const [isAssigningRole, setIsAssigningRole] = useState<Employee | null>(null)

  // Registration Form State
  const [newEmpId, setNewEmpId] = useState('')
  const [newEmpName, setNewEmpName] = useState('')
  const [newEmpEmail, setNewEmpEmail] = useState('')
  const [newEmpPassword, setNewEmpPassword] = useState('')
  const [isSubmittingRegister, setIsSubmittingRegister] = useState(false)

  // Role Assignment State
  const [selectedRole, setSelectedRole] = useState<'MANAGER' | 'WAITER' | 'COOK' | 'CASHIER'>(
    'WAITER',
  )
  const [isSubmittingRole, setIsSubmittingRole] = useState(false)

  const fetchEmployees = useCallback(async () => {
    setIsLoading(true)
    try {
      const res = await httpClient.get<Employee[]>('/v1/auth/employees')
      setEmployees(res.data || [])
    } catch (_err) {
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchEmployees()
  }, [fetchEmployees])

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newEmpId || !newEmpName.trim() || !newEmpEmail.trim() || !newEmpPassword) return

    setIsSubmittingRegister(true)
    try {
      const numericId = parseInt(newEmpId, 10)
      if (Number.isNaN(numericId)) {
        throw new Error('ID do colaborador deve ser um número inteiro.')
      }

      await httpClient.post('/v1/auth/employees', {
        id: numericId,
        name: newEmpName.trim(),
        email: newEmpEmail.trim(),
        password: newEmpPassword,
      })

      // Clean up form
      setNewEmpId('')
      setNewEmpName('')
      setNewEmpEmail('')
      setNewEmpPassword('')
      setIsCreatingEmployee(false)
      fetchEmployees()
      alert('Colaborador cadastrado no sistema global com sucesso!')
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } }; message?: string }
      const msg = error.response?.data?.detail || error.message || 'Erro ao registrar colaborador.'
      alert(`Falha no cadastro: ${msg}`)
    } finally {
      setIsSubmittingRegister(false)
    }
  }

  const handleAssignRole = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!isAssigningRole || !tenantId) return

    setIsSubmittingRole(true)
    try {
      const numericTenantId = parseInt(tenantId, 10)
      if (Number.isNaN(numericTenantId)) {
        throw new Error('ID do Tenant da franquia precisa ser numérico.')
      }

      await httpClient.post(`/v1/auth/employees/${isAssigningRole.id}/roles`, {
        tenant_id: numericTenantId,
        role_type: selectedRole,
      })

      setIsAssigningRole(null)
      fetchEmployees()
      alert(`Cargo de ${formatRoleLabel(selectedRole)} atribuído a ${isAssigningRole.name}!`)
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } }; message?: string }
      const msg = error.response?.data?.detail || error.message || 'Erro ao atribuir cargo.'
      alert(`Falha na atribuição: ${msg}`)
    } finally {
      setIsSubmittingRole(false)
    }
  }

  const handleToggleActive = async (emp: Employee) => {
    if (emp.id === currentEmployee?.id) {
      alert('Você não pode desativar a si mesmo!')
      return
    }
    try {
      await httpClient.post(`/v1/auth/employees/${emp.id}/toggle-active`)
      fetchEmployees()
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } }; message?: string }
      const msg = error.response?.data?.detail || error.message || 'Erro ao alterar status.'
      alert(`Falha ao alterar status: ${msg}`)
    }
  }

  const handleDeleteEmployee = async (emp: Employee) => {
    if (emp.id === currentEmployee?.id) {
      alert('Você não pode se remover da franquia!')
      return
    }
    if (
      !window.confirm(
        `Deseja realmente remover ${emp.name} desta franquia? Esta ação revogará o acesso dele a este estabelecimento.`,
      )
    ) {
      return
    }
    try {
      await httpClient.delete(`/v1/auth/employees/${emp.id}`)
      fetchEmployees()
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } }; message?: string }
      const msg = error.response?.data?.detail || error.message || 'Erro ao remover colaborador.'
      alert(`Falha ao remover: ${msg}`)
    }
  }

  const formatRoleLabel = (role: string | null) => {
    switch (role) {
      case 'MANAGER':
        return 'Gerente'
      case 'WAITER':
        return 'Garçom'
      case 'COOK':
        return 'Cozinheiro'
      case 'CASHIER':
        return 'Operador de Caixa'
      default:
        return 'Sem Cargo Ativo'
    }
  }

  const getRoleBadgeClasses = (role: string | null) => {
    switch (role) {
      case 'MANAGER':
        return 'border-amber-500/20 bg-amber-950/10 text-amber-400'
      case 'WAITER':
        return 'border-sky-500/20 bg-sky-950/10 text-sky-400'
      case 'COOK':
        return 'border-emerald-500/20 bg-emerald-950/10 text-emerald-400'
      case 'CASHIER':
        return 'border-purple-500/20 bg-purple-950/10 text-purple-400'
      default:
        return 'border-gray-800 bg-gray-900 text-gray-500'
    }
  }

  return (
    <Layout>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex items-center justify-between border-b border-gray-900/60 pb-3">
          <div>
            <h2 className="text-lg font-black text-white tracking-wide uppercase flex items-center gap-2">
              <Users className="h-5 w-5 text-brand-400" />
              Colaboradores da Franquia
            </h2>
            <p className="text-xs text-gray-550 font-medium mt-0.5">
              Cadastre novos membros da equipe e configure seus cargos de acesso
            </p>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={fetchEmployees}
              className="rounded-xl bg-gray-950/40 hover:bg-gray-900 border border-gray-900 px-3 py-2 text-xs font-bold text-gray-400 hover:text-white transition flex items-center gap-1"
              title="Recarregar"
            >
              <RefreshCcw className="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              onClick={() => setIsCreatingEmployee(true)}
              className="rounded-xl bg-brand-500 hover:bg-brand-600 px-4 py-2 text-xs font-bold text-white transition flex items-center gap-1.5"
            >
              <UserPlus className="h-4 w-4" />
              Novo Colaborador
            </button>
          </div>
        </div>

        {/* Info Box */}
        <div className="p-4 rounded-2xl border border-blue-950/40 bg-blue-950/5 flex gap-3 text-xs text-blue-400">
          <Lock className="h-4.5 w-4.5 shrink-0 mt-0.5" />
          <div className="leading-relaxed">
            <p className="font-bold">Como funciona a gestão de acessos?</p>
            <p className="text-blue-400/80 mt-0.5 text-[11px]">
              Primeiro, registre o colaborador no sistema global (e-mail corporativo único e ID
              numérico). Em seguida, utilize a ação de "Atribuir Cargo" para dar acesso a ele na
              franquia atual (ID do Tenant: {tenantId}).
            </p>
          </div>
        </div>

        {/* Employees Grid */}
        {isLoading && employees.length === 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3].map((n) => (
              <div
                key={n}
                className="h-40 rounded-2xl border border-gray-900 bg-gray-950/20 animate-pulse"
              />
            ))}
          </div>
        ) : employees.length === 0 ? (
          <div className="border border-dashed border-gray-850 rounded-2xl p-12 text-center text-xs text-gray-500 italic">
            Nenhum colaborador registrado no sistema.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {employees.map((emp) => (
              <EmployeeCard
                key={emp.id}
                emp={emp}
                currentEmployee={currentEmployee}
                getRoleBadgeClasses={getRoleBadgeClasses}
                formatRoleLabel={formatRoleLabel}
                onToggleActive={handleToggleActive}
                onDelete={handleDeleteEmployee}
                onAssignRole={(emp) => {
                  setSelectedRole(emp.role || 'WAITER')
                  setIsAssigningRole(emp)
                }}
              />
            ))}
          </div>
        )}

        {/* Modal: Register Employee */}
        {isCreatingEmployee && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
            <form
              onSubmit={handleRegister}
              className="w-full max-w-sm rounded-2xl glass-elevated p-6 space-y-4"
            >
              <div>
                <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
                  <UserPlus className="h-4 w-4 text-brand-400" />
                  Cadastrar Colaborador
                </h3>
                <p className="text-xs text-gray-550 mt-1">
                  Crie as credenciais globais do colaborador
                </p>
              </div>

              <div className="space-y-3">
                <div className="space-y-1.5">
                  <span className="block text-[10px] uppercase font-extrabold text-gray-400">
                    ID Numérico Único
                  </span>
                  <input
                    type="number"
                    required
                    placeholder="Ex: 5"
                    value={newEmpId}
                    onChange={(e) => setNewEmpId(e.target.value)}
                    className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input"
                  />
                </div>

                <div className="space-y-1.5">
                  <span className="block text-[10px] uppercase font-extrabold text-gray-400">
                    Nome Completo
                  </span>
                  <input
                    type="text"
                    required
                    placeholder="Ex: Ana Souza"
                    value={newEmpName}
                    onChange={(e) => setNewEmpName(e.target.value)}
                    className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input"
                  />
                </div>

                <div className="space-y-1.5">
                  <span className="block text-[10px] uppercase font-extrabold text-gray-400">
                    E-mail Corporativo
                  </span>
                  <input
                    type="email"
                    required
                    placeholder="Ex: ana.souza@comandafacil.com"
                    value={newEmpEmail}
                    onChange={(e) => setNewEmpEmail(e.target.value)}
                    className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input"
                  />
                </div>

                <div className="space-y-1.5">
                  <span className="block text-[10px] uppercase font-extrabold text-gray-400">
                    Senha Inicial (Mín. 6 caracteres)
                  </span>
                  <input
                    type="password"
                    required
                    minLength={6}
                    placeholder="••••••••"
                    value={newEmpPassword}
                    onChange={(e) => setNewEmpPassword(e.target.value)}
                    className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input"
                  />
                </div>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsCreatingEmployee(false)}
                  disabled={isSubmittingRegister}
                  className="flex-1 rounded-xl border border-gray-850 hover:bg-white/[0.02] py-2.5 text-xs font-bold text-gray-400 transition"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingRegister}
                  className="flex-1 rounded-xl bg-brand-500 hover:bg-brand-600 py-2.5 text-xs font-bold text-white transition flex items-center justify-center gap-1"
                >
                  {isSubmittingRegister ? (
                    <span className="h-3 w-3 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  ) : null}
                  Cadastrar
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Modal: Assign Role */}
        {isAssigningRole && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
            <form
              onSubmit={handleAssignRole}
              className="w-full max-w-sm rounded-2xl glass-elevated p-6 space-y-4"
            >
              <div>
                <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
                  <Shield className="h-4 w-4 text-brand-400" />
                  Atribuir Cargo
                </h3>
                <p className="text-xs text-gray-550 mt-1">
                  Atribua uma função para {isAssigningRole.name} na Franquia ID {tenantId}
                </p>
              </div>

              <div className="space-y-3">
                <div className="space-y-1.5">
                  <span className="block text-[10px] uppercase font-extrabold text-gray-400">
                    Selecione o Cargo
                  </span>
                  <select
                    value={selectedRole}
                    onChange={(e) =>
                      setSelectedRole(e.target.value as 'MANAGER' | 'WAITER' | 'COOK' | 'CASHIER')
                    }
                    className="w-full rounded-xl px-4 py-3 text-xs text-white glass-input bg-[#0b0b11]"
                  >
                    <option value="WAITER">Garçom (Fila de Comandas)</option>
                    <option value="COOK">Cozinheiro (Painel KDS)</option>
                    <option value="CASHIER">Operador de Caixa (Checkout e Histórico)</option>
                    <option value="MANAGER">Gerente (Acesso Administrativo Total)</option>
                  </select>
                </div>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsAssigningRole(null)}
                  disabled={isSubmittingRole}
                  className="flex-1 rounded-xl border border-gray-850 hover:bg-white/[0.02] py-2.5 text-xs font-bold text-gray-400 transition"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingRole}
                  className="flex-1 rounded-xl bg-brand-500 hover:bg-brand-600 py-2.5 text-xs font-bold text-white transition flex items-center justify-center gap-1"
                >
                  {isSubmittingRole ? (
                    <span className="h-3 w-3 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  ) : null}
                  Atribuir Cargo
                </button>
              </div>
            </form>
          </div>
        )}
      </div>
    </Layout>
  )
}
