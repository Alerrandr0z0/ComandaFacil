import { ClipboardList, Coffee, Flame, LogOut, Shield, TrendingUp } from 'lucide-react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '@/features/auth/auth_context'
import { useTenant } from '@/shared/hooks/useTenant'

export default function Layout({ children }: { children: React.ReactNode }) {
  const { employee, logout } = useAuth()
  const { tenantId } = useTenant()
  const navigate = useNavigate()
  const location = useLocation()

  const navItems = [
    { label: 'Mesas & Pedidos', path: '/orders', icon: ClipboardList },
    { label: 'Cozinha KDS', path: '/kitchen', icon: Flame },
    { label: 'Controle Estoque', path: '/stock', icon: Coffee },
    { label: 'Analytics', path: '/analytics', icon: TrendingUp },
  ]

  const handleLogout = async () => {
    if (window.confirm('Deseja realmente sair da sessão?')) {
      await logout()
      navigate('/login')
    }
  }

  return (
    <div className="flex min-h-screen bg-gray-950 text-gray-100 font-sans">
      {/* Sidebar Navigation */}
      <aside className="hidden md:flex md:w-64 flex-col border-r border-gray-900 bg-gray-950/70 backdrop-blur-md">
        {/* Brand/Logo */}
        <div className="flex h-16 items-center gap-2.5 px-6 border-b border-gray-900">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-500 text-white font-bold text-lg shadow-md shadow-brand-500/20">
            C
          </div>
          <div>
            <h1 className="text-sm font-black tracking-tight text-white uppercase">ComandaFácil</h1>
            <span className="text-[10px] text-gray-500">Franquia ID: {tenantId}</span>
          </div>
        </div>

        {/* Menu Navigation Links */}
        <nav className="flex-1 space-y-1.5 px-4 py-6">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = location.pathname === item.path
            return (
              <button
                type="button"
                key={item.path}
                onClick={() => navigate(item.path)}
                className={`flex w-full items-center gap-3 rounded-xl px-4 py-3 text-xs font-bold transition duration-200 ${
                  isActive
                    ? 'bg-brand-500/10 border border-brand-500/20 text-brand-400'
                    : 'border border-transparent text-gray-400 hover:text-white hover:bg-gray-900/50'
                }`}
              >
                <Icon className="h-4.5 w-4.5" />
                {item.label}
              </button>
            )
          })}
        </nav>

        {/* User Card */}
        <div className="p-4 border-t border-gray-900 space-y-3">
          <div className="flex items-center gap-3 bg-gray-900/40 border border-gray-850 p-3 rounded-xl">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-500/10 text-brand-400 border border-brand-900/40">
              <Shield className="h-4.5 w-4.5" />
            </div>
            <div className="overflow-hidden">
              <p className="text-xs font-bold text-gray-200 truncate">{employee?.name}</p>
              <p className="text-[9px] text-gray-500 truncate">{employee?.email}</p>
            </div>
          </div>

          <button
            type="button"
            onClick={handleLogout}
            className="flex w-full items-center justify-center gap-2 rounded-xl border border-red-900 bg-red-950/10 hover:bg-red-900/25 px-4 py-2.5 text-xs font-bold text-red-400 transition"
          >
            <LogOut className="h-4 w-4" />
            Encerrar Sessão
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Mobile Header */}
        <header className="flex h-16 items-center justify-between border-b border-gray-900 bg-gray-950/70 backdrop-blur-md px-6 md:hidden">
          <div className="flex items-center gap-2">
            <div className="flex h-7.5 w-7.5 items-center justify-center rounded bg-brand-500 text-white font-bold text-sm">
              C
            </div>
            <h1 className="text-xs font-black tracking-tight uppercase">ComandaFácil</h1>
          </div>
          <button
            type="button"
            onClick={handleLogout}
            className="rounded-lg p-1.5 border border-red-900 text-red-400 hover:bg-red-900/25 transition"
            title="Sair"
          >
            <LogOut className="h-4.5 w-4.5" />
          </button>
        </header>

        {/* Dynamic Page Rendering */}
        <main className="flex-1 p-6 md:p-8 overflow-y-auto max-w-7xl w-full mx-auto">
          {children}
        </main>

        {/* Mobile bottom tabs */}
        <nav className="flex h-14 border-t border-gray-900 bg-gray-950/80 backdrop-blur-md md:hidden">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = location.pathname === item.path
            return (
              <button
                type="button"
                key={item.path}
                onClick={() => navigate(item.path)}
                className={`flex flex-1 flex-col items-center justify-center gap-1 transition ${
                  isActive ? 'text-brand-400' : 'text-gray-500'
                }`}
              >
                <Icon className="h-4 w-4" />
                <span className="text-[8px] font-bold">{item.label.split(' ')[0]}</span>
              </button>
            )
          })}
        </nav>
      </div>
    </div>
  )
}
