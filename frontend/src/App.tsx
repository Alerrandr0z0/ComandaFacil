import type React from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from '@/features/auth/auth_context'
import AnalyticsPage from '@/pages/analytics'
import KitchenPage from '@/pages/kitchen'
import LoginPage from '@/pages/login'
import OrdersPage from '@/pages/orders'
import StockPage from '@/pages/stock'

function ProtectedRoute({
  children,
  allowedRoles,
}: {
  children: React.ReactNode
  allowedRoles?: string[]
}) {
  const { isAuthenticated, isLoading, employee } = useAuth()

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-950">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-500 border-t-transparent" />
      </div>
    )
  }

  if (!isAuthenticated || !employee) {
    return <Navigate to="/login" replace />
  }

  if (allowedRoles && employee.role && !allowedRoles.includes(employee.role)) {
    const defaultRedirect = employee.role === 'COOK' ? '/kitchen' : '/orders'
    return <Navigate to={defaultRedirect} replace />
  }

  return <>{children}</>
}

function RootRedirect() {
  const { employee } = useAuth()
  const defaultRedirect = employee?.role === 'COOK' ? '/kitchen' : '/orders'
  return <Navigate to={defaultRedirect} replace />
}

export default function App() {
  const { isAuthenticated, employee } = useAuth()

  // Default login landing redirect based on role
  const defaultLoginRedirect = employee?.role === 'COOK' ? '/kitchen' : '/orders'

  return (
    <Routes>
      <Route
        path="/login"
        element={isAuthenticated ? <Navigate to={defaultLoginRedirect} replace /> : <LoginPage />}
      />

      <Route
        path="/"
        element={
          <ProtectedRoute>
            <RootRedirect />
          </ProtectedRoute>
        }
      />

      <Route
        path="/orders"
        element={
          <ProtectedRoute allowedRoles={['MANAGER', 'WAITER', 'CASHIER']}>
            <OrdersPage />
          </ProtectedRoute>
        }
      />

      <Route
        path="/kitchen"
        element={
          <ProtectedRoute allowedRoles={['MANAGER', 'COOK']}>
            <KitchenPage />
          </ProtectedRoute>
        }
      />

      <Route
        path="/stock"
        element={
          <ProtectedRoute allowedRoles={['MANAGER']}>
            <StockPage />
          </ProtectedRoute>
        }
      />

      <Route
        path="/analytics"
        element={
          <ProtectedRoute allowedRoles={['MANAGER']}>
            <AnalyticsPage />
          </ProtectedRoute>
        }
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
