import {
  ClipboardList,
  Coffee,
  Flame,
  History,
  LogOut,
  Shield,
  TrendingUp,
  Users,
  Utensils,
} from 'lucide-react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '@/features/auth/auth_context'
import { useTenant } from '@/shared/hooks/useTenant'

export default function Layout({ children }: { children: React.ReactNode }) {
  const { employee, logout } = useAuth()
  const { tenantId } = useTenant()
  const navigate = useNavigate()
  const location = useLocation()

  const navItems = [
    // Admin specific items
    {
      label: 'Painel Geral',
      path: '/admin',
      icon: TrendingUp,
      roles: ['SUPER_ADMIN'],
    },
    {
      label: 'Franquias',
      path: '/admin/tenants',
      icon: Utensils,
      roles: ['SUPER_ADMIN'],
    },
    {
      label: 'Fornecedores',
      path: '/admin/suppliers',
      icon: Coffee,
      roles: ['SUPER_ADMIN'],
    },
    {
      label: 'Gerentes',
      path: '/admin/managers',
      icon: Users,
      roles: ['SUPER_ADMIN'],
    },
    {
      label: 'Solicitações',
      path: '/admin/requests',
      icon: ClipboardList,
      roles: ['SUPER_ADMIN'],
    },
    // Tenant-specific items
    {
      label: 'Salão',
      path: '/orders',
      icon: ClipboardList,
      roles: ['MANAGER', 'WAITER', 'CASHIER'],
    },
    { label: 'Cozinha', path: '/kitchen', icon: Flame, roles: ['MANAGER', 'COOK'] },
    { label: 'Estoque', path: '/stock', icon: Coffee, roles: ['MANAGER'] },
    { label: 'Analytics', path: '/analytics', icon: TrendingUp, roles: ['MANAGER'] },
    { label: 'Catálogo', path: '/catalog', icon: Utensils, roles: ['MANAGER'] },
    { label: 'Cardápios', path: '/menu-manager', icon: ClipboardList, roles: ['MANAGER'] },
    { label: 'Colaboradores', path: '/employees', icon: Users, roles: ['MANAGER'] },
    { label: 'Histórico', path: '/history', icon: History, roles: ['MANAGER', 'CASHIER'] },
  ]

  // Filter navigation items based on the employee's role
  const allowedNavItems = navItems.filter((item) => {
    if (!employee?.role) return false
    return item.roles.includes(employee.role)
  })

  const handleLogout = async () => {
    if (window.confirm('Deseja realmente sair da sessão?')) {
      await logout()
      navigate('/login')
    }
  }

  const isGlobalAdmin = employee?.role === 'SUPER_ADMIN'

  return (
    <div className="flex min-h-screen bg-[#050508] text-gray-150 font-sans">
      {/* Sidebar Navigation - Glassmorphic design */}
      <aside className="hidden md:flex md:w-64 flex-col border-r border-gray-900 bg-gray-950/40 backdrop-blur-md glass-card">
        {/* Brand/Logo */}
        <div className="flex h-16 items-center gap-2.5 px-6 border-b border-gray-900/60">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-tr from-brand-600 to-brand-400 text-white font-black text-xl shadow-lg shadow-brand-500/20">
            CF
          </div>
          <div>
            <h1 className="text-sm font-black tracking-wider text-white uppercase">ComandaFácil</h1>
            <span className="text-[10px] font-medium text-brand-400/80">
              {isGlobalAdmin ? 'Administração Global' : `Franquia ID: ${tenantId}`}
            </span>
          </div>
        </div>

        {/* Menu Navigation Links */}
        <nav className="flex-1 space-y-2 px-4 py-6">
          {allowedNavItems.map((item) => {
            const Icon = item.icon
            const isActive = location.pathname === item.path
            return (
              <button
                type="button"
                key={item.path}
                onClick={() => navigate(item.path)}
                className={`flex w-full items-center gap-3 rounded-xl px-4 py-3.5 text-xs font-bold transition-all duration-300 ${
                  isActive
                    ? 'bg-brand-500/10 border border-brand-500/30 text-brand-400 shadow-md shadow-brand-500/5'
                    : 'border border-transparent text-gray-400 hover:text-white hover:bg-white/[0.03]'
                }`}
              >
                <Icon
                  className={`h-4.5 w-4.5 transition-transform duration-300 ${isActive ? 'scale-110' : ''}`}
                />
                {item.label}
              </button>
            )
          })}
        </nav>

        {/* User Card */}
        <div className="p-4 border-t border-gray-900/60 space-y-3">
          <div className="flex items-center gap-3 bg-gray-900/20 border border-gray-850 p-3 rounded-xl">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-500/10 text-brand-400 border border-brand-500/20 shadow-inner">
              <Shield className="h-4 w-4" />
            </div>
            <div className="overflow-hidden">
              <p className="text-xs font-bold text-gray-200 truncate">{employee?.name}</p>
              <div className="flex items-center gap-1.5">
                <span className="text-[8px] uppercase tracking-wider font-extrabold px-1.5 py-0.5 rounded bg-brand-500/10 border border-brand-500/20 text-brand-400">
                  {employee?.role || 'N/A'}
                </span>
              </div>
            </div>
          </div>

          <button
            type="button"
            onClick={handleLogout}
            className="flex w-full items-center justify-center gap-2 rounded-xl border border-red-950/40 bg-red-950/10 hover:bg-red-900/20 px-4 py-2.5 text-xs font-bold text-red-400 transition-all duration-300 hover:shadow-md"
          >
            <LogOut className="h-4 w-4" />
            Encerrar Sessão
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Mobile Header */}
        <header className="flex h-16 items-center justify-between border-b border-gray-900/60 bg-gray-950/40 backdrop-blur-md px-6 md:hidden">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-tr from-brand-600 to-brand-400 text-white font-black text-sm">
              CF
            </div>
            <div>
              <h1 className="text-xs font-black tracking-widest uppercase">ComandaFácil</h1>
              <span className="text-[8px] font-bold text-brand-400/80">
                {isGlobalAdmin ? 'Administração Global' : `ID: ${tenantId}`}
              </span>
            </div>
          </div>
          <button
            type="button"
            onClick={handleLogout}
            className="rounded-lg p-2 border border-red-950/40 text-red-400 bg-red-950/5 hover:bg-red-900/20 transition-all duration-300"
            title="Sair"
          >
            <LogOut className="h-4.5 w-4.5" />
          </button>
        </header>

        {/* Dynamic Page Rendering */}
        <main className="flex-1 p-4 md:p-8 overflow-y-auto w-full mx-auto animate-fade-in">
          {children}
        </main>

        {/* Mobile bottom tabs - Dynamic based on roles */}
        <nav className="flex h-14 border-t border-gray-900/60 bg-gray-950/60 backdrop-blur-md md:hidden">
          {allowedNavItems.map((item) => {
            const Icon = item.icon
            const isActive = location.pathname === item.path
            return (
              <button
                type="button"
                key={item.path}
                onClick={() => navigate(item.path)}
                className={`flex flex-1 flex-col items-center justify-center gap-1 transition-all duration-300 ${
                  isActive ? 'text-brand-400 scale-105' : 'text-gray-500 hover:text-gray-300'
                }`}
              >
                <Icon className="h-4 w-4" />
                <span className="text-[8px] font-bold tracking-wider">{item.label}</span>
              </button>
            )
          })}
        </nav>
      </div>
    </div>
  )
}
