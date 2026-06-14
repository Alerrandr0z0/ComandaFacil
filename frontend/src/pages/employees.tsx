import {
  ClipboardList,
  History,
  Lock,
  Power,
  RefreshCcw,
  Search,
  Shield,
  ShieldCheck,
  SlidersHorizontal,
  Trash,
  UserPlus,
  Users,
  X,
} from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
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

interface PermissionOverride {
  id: number
  employee_id: number
  action: string
  granted: boolean
}

interface AuditEntry {
  id: number
  actor_name: string
  action: string
  entity_type: string | null
  entity_id: string | null
  details: string | null
  created_at: string | null
}

const ALL_ACTIONS = [
  'MANAGE_MENU',
  'CREATE_ORDER',
  'ADJUST_STOCK',
  'MANAGE_EMPLOYEES',
  'VIEW_ANALYTICS',
]

const ACTION_LABELS: Record<string, string> = {
  MANAGE_MENU: 'Gerenciar Cardápio',
  CREATE_ORDER: 'Criar Comandas',
  ADJUST_STOCK: 'Ajustar Estoque',
  MANAGE_EMPLOYEES: 'Gerenciar Colaboradores',
  VIEW_ANALYTICS: 'Ver Analytics',
}

const ROLE_LABELS: Record<string, string> = {
  MANAGER: 'Gerente',
  WAITER: 'Garçom',
  COOK: 'Cozinheiro',
  CASHIER: 'Operador de Caixa',
}

const ROLE_COLORS: Record<string, string> = {
  MANAGER: 'border-amber-500/20 bg-amber-950/10 text-amber-400',
  WAITER: 'border-sky-500/20 bg-sky-950/10 text-sky-400',
  COOK: 'border-emerald-500/20 bg-emerald-950/10 text-emerald-400',
  CASHIER: 'border-purple-500/20 bg-purple-950/10 text-purple-400',
}

function formatRoleLabel(role: string | null) {
  if (!role) return 'Sem Cargo Ativo'
  return ROLE_LABELS[role] || role
}

function EmployeeRow({
  emp,
  isSelf,
  onAssignRole,
  onEditPermissions,
  onToggleActive,
  onDelete,
}: {
  emp: Employee
  isSelf: boolean
  onAssignRole: (emp: Employee) => void
  onEditPermissions: (emp: Employee) => void
  onToggleActive: (emp: Employee) => void
  onDelete: (emp: Employee) => void
}) {
  return (
    <tr className={`transition-colors hover:bg-gray-950/30 ${isSelf ? 'bg-brand-950/5' : ''}`}>
      <td className="px-4 py-3 text-gray-500 font-mono">{emp.id}</td>
      <td className="px-4 py-3">
        <span className="text-gray-200 font-semibold">
          {emp.name}
          {isSelf && <span className="text-[9px] text-brand-400 ml-1.5 font-normal">(Você)</span>}
        </span>
      </td>
      <td className="px-4 py-3 text-gray-400">{emp.email}</td>
      <td className="px-4 py-3">
        <span
          className={`inline-block text-[9px] px-2 py-0.5 rounded-full border uppercase tracking-wider font-extrabold ${
            ROLE_COLORS[emp.role ?? ''] || 'border-gray-800 bg-gray-900 text-gray-500'
          }`}
        >
          {formatRoleLabel(emp.role)}
        </span>
      </td>
      <td className="px-4 py-3">
        <span
          className={`inline-block text-[8px] px-1.5 py-0.5 rounded-full border uppercase tracking-wider font-extrabold ${
            emp.is_active
              ? 'border-emerald-500/25 bg-emerald-500/10 text-emerald-400'
              : 'border-rose-500/25 bg-rose-500/10 text-rose-450'
          }`}
        >
          {emp.is_active ? 'Ativo' : 'Suspenso'}
        </span>
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center justify-end gap-1">
          <button
            type="button"
            onClick={() => onEditPermissions(emp)}
            className="p-1.5 rounded-lg border border-gray-850 bg-gray-950/40 text-gray-500 hover:text-brand-400 hover:border-brand-500/30 transition"
            title="Permissões Individuais"
          >
            <ShieldCheck className="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            onClick={() => onAssignRole(emp)}
            className="p-1.5 rounded-lg border border-gray-850 bg-gray-950/40 text-gray-500 hover:text-brand-400 hover:border-brand-500/30 transition"
            title="Atribuir Cargo"
          >
            <Shield className="h-3.5 w-3.5" />
          </button>
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
      </td>
    </tr>
  )
}

function PermissionCell({
  action,
  permissions,
  onToggle,
}: {
  action: string
  permissions: PermissionOverride[]
  onToggle: (action: string, granted: boolean | null, permissionId?: number) => void
}) {
  const override = permissions.find((p) => p.action === action)
  const state = override === undefined ? null : override.granted
  return (
    <td className="px-3 py-2.5 text-center">
      <button
        type="button"
        onClick={() => onToggle(action, state, override?.id)}
        className={`inline-flex items-center justify-center w-7 h-7 rounded-lg border transition ${
          state === true
            ? 'border-emerald-500/30 bg-emerald-500/15 text-emerald-400'
            : state === false
              ? 'border-rose-500/30 bg-rose-500/15 text-rose-400'
              : 'border-gray-800 bg-gray-950/40 text-gray-600 hover:border-gray-700 hover:text-gray-400'
        }`}
        title={
          state === null
            ? 'Clique para conceder'
            : state
              ? 'Clique para negar'
              : 'Clique para remover override'
        }
      >
        {state === true ? (
          <ShieldCheck className="h-3.5 w-3.5" />
        ) : state === false ? (
          <X className="h-3.5 w-3.5" />
        ) : (
          <span className="text-gray-600">&mdash;</span>
        )}
      </button>
    </td>
  )
}

export default function EmployeesPage() {
  const { tenantId } = useTenant()
  const { employee: currentEmployee } = useAuth()

  const [employees, setEmployees] = useState<Employee[]>([])
  const [isLoading, setIsLoading] = useState(true)

  const [searchQuery, setSearchQuery] = useState('')
  const [roleFilter, setRoleFilter] = useState<string>('all')
  const [statusFilter, setStatusFilter] = useState<string>('all')

  const [isCreatingEmployee, setIsCreatingEmployee] = useState(false)
  const [isAssigningRole, setIsAssigningRole] = useState<Employee | null>(null)

  const [newEmpId, setNewEmpId] = useState('')
  const [newEmpName, setNewEmpName] = useState('')
  const [newEmpEmail, setNewEmpEmail] = useState('')
  const [newEmpPassword, setNewEmpPassword] = useState('')
  const [isSubmittingRegister, setIsSubmittingRegister] = useState(false)

  const [selectedRole, setSelectedRole] = useState<'MANAGER' | 'WAITER' | 'COOK' | 'CASHIER'>(
    'WAITER',
  )
  const [isSubmittingRole, setIsSubmittingRole] = useState(false)

  const [permissions, setPermissions] = useState<PermissionOverride[]>([])
  const [permissionsTarget, setPermissionsTarget] = useState<Employee | null>(null)
  const [isLoadingPermissions, setIsLoadingPermissions] = useState(false)

  const [auditLogs, setAuditLogs] = useState<AuditEntry[]>([])
  const [isAuditOpen, setIsAuditOpen] = useState(false)
  const [isLoadingAudit, setIsLoadingAudit] = useState(false)

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

  const fetchPermissions = useCallback(async (employeeId: number) => {
    setIsLoadingPermissions(true)
    try {
      const res = await httpClient.get<PermissionOverride[]>(
        `/v1/auth/employees/${employeeId}/permissions`,
      )
      setPermissions(res.data || [])
    } catch (_err) {
    } finally {
      setIsLoadingPermissions(false)
    }
  }, [])

  const fetchAuditLogs = useCallback(async () => {
    setIsLoadingAudit(true)
    try {
      const res = await httpClient.get<AuditEntry[]>('/v1/auth/audit-logs')
      setAuditLogs(res.data || [])
    } catch (_err) {
    } finally {
      setIsLoadingAudit(false)
    }
  }, [])

  useEffect(() => {
    fetchEmployees()
  }, [fetchEmployees])

  const filteredEmployees = useMemo(() => {
    let result = employees

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      result = result.filter(
        (e) =>
          e.name.toLowerCase().includes(q) ||
          e.email.toLowerCase().includes(q) ||
          String(e.id).includes(q),
      )
    }

    if (roleFilter !== 'all') {
      if (roleFilter === 'none') {
        result = result.filter((e) => e.role === null)
      } else {
        result = result.filter((e) => e.role === roleFilter)
      }
    }

    if (statusFilter !== 'all') {
      result = result.filter((e) => (statusFilter === 'active' ? e.is_active : !e.is_active))
    }

    return result
  }, [employees, searchQuery, roleFilter, statusFilter])

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

      setNewEmpId('')
      setNewEmpName('')
      setNewEmpEmail('')
      setNewEmpPassword('')
      setIsCreatingEmployee(false)
      fetchEmployees()
      setSelectedRole('WAITER')
      setIsAssigningRole({
        id: numericId,
        name: newEmpName.trim(),
        email: newEmpEmail.trim(),
        role: null,
        is_active: true,
      })
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

  const handleTogglePermission = async (
    action: string,
    currentGranted: boolean | null,
    permissionId?: number,
  ) => {
    const empId = permissionsTarget?.id
    if (!empId) return
    if (permissionId) {
      await httpClient.delete(`/v1/auth/employees/${empId}/permissions/${permissionId}`)
    } else {
      await httpClient.put(`/v1/auth/employees/${empId}/permissions`, {
        action,
        granted: !currentGranted,
      })
    }
    fetchPermissions(empId)
  }

  const openPermissions = (emp: Employee) => {
    setPermissionsTarget(emp)
    fetchPermissions(emp.id)
  }

  const closePermissions = () => {
    setPermissionsTarget(null)
    setPermissions([])
  }

  const openAudit = () => {
    fetchAuditLogs()
    setIsAuditOpen(true)
  }

  return (
    <Layout>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex items-center justify-between border-b border-gray-900/60 pb-3 flex-wrap gap-3">
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
              onClick={openAudit}
              className="rounded-xl bg-gray-950/40 hover:bg-gray-900 border border-gray-900 px-3 py-2 text-xs font-bold text-gray-400 hover:text-white transition flex items-center gap-1"
              title="Histórico de Auditoria"
            >
              <ClipboardList className="h-3.5 w-3.5" />
              Auditoria
            </button>
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
              numérico). Em seguida, utilize a ação de &quot;Atribuir Cargo&quot; para dar acesso a
              ele na franquia atual (ID do Tenant: {tenantId}).
            </p>
          </div>
        </div>

        {/* Search & Filters */}
        <div className="flex items-center gap-3 flex-wrap">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-600" />
            <input
              type="text"
              placeholder="Buscar por nome, email ou ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-xl pl-9 pr-4 py-2.5 text-xs text-white glass-input"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-600 hover:text-gray-400"
              >
                <X className="h-3 w-3" />
              </button>
            )}
          </div>

          <div className="flex items-center gap-2">
            <SlidersHorizontal className="h-3.5 w-3.5 text-gray-600" />
            <select
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
              className="rounded-xl px-3 py-2.5 text-xs text-white glass-input bg-[#0b0b11]"
            >
              <option value="all">Todos os Cargos</option>
              <option value="none">Sem Cargo</option>
              <option value="MANAGER">Gerente</option>
              <option value="WAITER">Garçom</option>
              <option value="COOK">Cozinheiro</option>
              <option value="CASHIER">Operador de Caixa</option>
            </select>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="rounded-xl px-3 py-2.5 text-xs text-white glass-input bg-[#0b0b11]"
            >
              <option value="all">Todos os Status</option>
              <option value="active">Ativo</option>
              <option value="inactive">Suspenso</option>
            </select>
          </div>
        </div>

        {/* Table */}
        {isLoading && employees.length === 0 ? (
          <div className="rounded-2xl border border-gray-900 bg-gray-950/20 animate-pulse h-64" />
        ) : filteredEmployees.length === 0 ? (
          <div className="border border-dashed border-gray-850 rounded-2xl p-12 text-center text-xs text-gray-500 italic">
            {employees.length === 0
              ? 'Nenhum colaborador registrado no sistema.'
              : 'Nenhum colaborador corresponde aos filtros aplicados.'}
          </div>
        ) : (
          <div className="overflow-x-auto rounded-2xl border border-gray-900">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-gray-900 bg-gray-950/40">
                  <th className="text-left px-4 py-3 text-[10px] uppercase font-extrabold text-gray-500 tracking-wider">
                    ID
                  </th>
                  <th className="text-left px-4 py-3 text-[10px] uppercase font-extrabold text-gray-500 tracking-wider">
                    Nome
                  </th>
                  <th className="text-left px-4 py-3 text-[10px] uppercase font-extrabold text-gray-500 tracking-wider">
                    Email
                  </th>
                  <th className="text-left px-4 py-3 text-[10px] uppercase font-extrabold text-gray-500 tracking-wider">
                    Cargo
                  </th>
                  <th className="text-left px-4 py-3 text-[10px] uppercase font-extrabold text-gray-500 tracking-wider">
                    Status
                  </th>
                  <th className="text-right px-4 py-3 text-[10px] uppercase font-extrabold text-gray-500 tracking-wider">
                    Ações
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-900/60">
                {filteredEmployees.map((emp) => (
                  <EmployeeRow
                    key={emp.id}
                    emp={emp}
                    isSelf={emp.id === currentEmployee?.id}
                    onEditPermissions={openPermissions}
                    onAssignRole={(e) => {
                      setSelectedRole(e.role || 'WAITER')
                      setIsAssigningRole(e)
                    }}
                    onToggleActive={handleToggleActive}
                    onDelete={handleDeleteEmployee}
                  />
                ))}
              </tbody>
            </table>
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

        {/* Modal: Employee Permissions */}
        {permissionsTarget && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
            <div className="w-full max-w-lg rounded-2xl glass-elevated p-6 space-y-4 max-h-[80vh] flex flex-col">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
                    <ShieldCheck className="h-4 w-4 text-brand-400" />
                    Permissões: {permissionsTarget.name}
                  </h3>
                  <p className="text-xs text-gray-550 mt-1">
                    Sobrescreva permissões individuais. Deixe como &mdash; para usar a regra padrão
                    do cargo ({formatRoleLabel(permissionsTarget.role)}).
                  </p>
                </div>
                <button
                  type="button"
                  onClick={closePermissions}
                  className="p-1.5 rounded-lg border border-gray-850 hover:bg-gray-900 text-gray-500 hover:text-white transition"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="overflow-x-auto flex-1">
                {isLoadingPermissions ? (
                  <div className="h-32 rounded-xl bg-gray-950/20 animate-pulse" />
                ) : (
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-gray-900">
                        <th className="text-left px-3 py-2 text-[10px] uppercase font-extrabold text-gray-500 tracking-wider">
                          Ação
                        </th>
                        <th className="text-center px-3 py-2 text-[10px] uppercase font-extrabold text-gray-500 tracking-wider">
                          Status
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-900/60">
                      {ALL_ACTIONS.map((action) => (
                        <tr key={action} className="hover:bg-gray-950/30 transition-colors">
                          <td className="px-3 py-2.5 text-gray-300 font-medium">
                            {ACTION_LABELS[action]}
                          </td>
                          <PermissionCell
                            action={action}
                            permissions={permissions}
                            onToggle={handleTogglePermission}
                          />
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>

              <div className="flex items-center justify-between pt-2 border-t border-gray-900/60">
                <div className="flex items-center gap-3 text-[10px] text-gray-600">
                  <span className="flex items-center gap-1">
                    <ShieldCheck className="h-3 w-3 text-emerald-400" /> Concedido
                  </span>
                  <span className="flex items-center gap-1">
                    <X className="h-3 w-3 text-rose-400" /> Negado
                  </span>
                  <span className="flex items-center gap-1">
                    <span>&mdash;</span> Padrão do cargo
                  </span>
                </div>
                <button
                  type="button"
                  onClick={closePermissions}
                  className="rounded-xl bg-brand-500 hover:bg-brand-600 px-4 py-2 text-[10px] font-bold text-white transition"
                >
                  Fechar
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Modal: Audit Log */}
        {isAuditOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
            <div className="w-full max-w-2xl rounded-2xl glass-elevated p-6 space-y-4 max-h-[80vh] flex flex-col">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
                    <History className="h-4 w-4 text-brand-400" />
                    Histórico de Auditoria
                  </h3>
                  <p className="text-xs text-gray-550 mt-1">
                    Registro de ações realizadas na franquia
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setIsAuditOpen(false)}
                  className="p-1.5 rounded-lg border border-gray-850 hover:bg-gray-900 text-gray-500 hover:text-white transition"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="overflow-y-auto flex-1 space-y-2">
                {isLoadingAudit ? (
                  <div className="h-32 rounded-xl bg-gray-950/20 animate-pulse" />
                ) : auditLogs.length === 0 ? (
                  <div className="border border-dashed border-gray-850 rounded-2xl p-8 text-center text-xs text-gray-500 italic">
                    Nenhum registro de auditoria encontrado.
                  </div>
                ) : (
                  auditLogs.map((entry) => (
                    <div
                      key={entry.id}
                      className="p-3 rounded-xl border border-gray-900 bg-gray-950/15 text-xs"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-gray-200 font-semibold">{entry.action}</span>
                        <span className="text-[10px] text-gray-600">
                          {entry.created_at
                            ? new Date(entry.created_at).toLocaleString('pt-BR')
                            : ''}
                        </span>
                      </div>
                      <div className="mt-1 text-gray-500 space-y-0.5">
                        {entry.actor_name && (
                          <p>
                            Por: <span className="text-gray-400">{entry.actor_name}</span>
                          </p>
                        )}
                        {entry.entity_type && entry.entity_id && (
                          <p>
                            {entry.entity_type}:{' '}
                            <span className="text-gray-400">{entry.entity_id}</span>
                          </p>
                        )}
                        {entry.details && <p className="text-gray-500">{entry.details}</p>}
                      </div>
                    </div>
                  ))
                )}
              </div>

              <div className="flex justify-end pt-2 border-t border-gray-900/60">
                <button
                  type="button"
                  onClick={() => setIsAuditOpen(false)}
                  className="rounded-xl bg-brand-500 hover:bg-brand-600 px-4 py-2 text-[10px] font-bold text-white transition"
                >
                  Fechar
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  )
}
