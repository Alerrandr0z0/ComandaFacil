import { createContext, type ReactNode, useCallback, useContext, useEffect, useState } from 'react'
import { useTenant } from '@/shared/hooks/useTenant'
import { httpClient } from '@/shared/lib/http_client'

interface Employee {
  id: number
  name: string
  email: string
  role: 'MANAGER' | 'WAITER' | 'COOK' | 'CASHIER' | 'SUPER_ADMIN' | null
}

interface AuthContextType {
  isAuthenticated: boolean
  isLoading: boolean
  employee: Employee | null
  login: (email: string, password: string, tenantId: number) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [employee, setEmployee] = useState<Employee | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const { setTenantId } = useTenant()

  const fetchProfile = useCallback(async () => {
    try {
      const response = await httpClient.get<Employee>('/v1/auth/me')
      setEmployee(response.data)
    } catch {
      // In case of invalid/expired token, http_client interceptor clears storage
      setEmployee(null)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    const token = localStorage.getItem('auth_token')
    if (token) {
      fetchProfile()
    } else {
      setIsLoading(false)
    }
  }, [fetchProfile])

  const login = async (email: string, password: string, tenantId: number) => {
    setIsLoading(true)
    try {
      // 1. Post to login endpoint
      const response = await httpClient.post<{ session_id: string; expires_at: string }>(
        '/v1/auth/login',
        {
          email,
          password,
          tenant_id: tenantId,
        },
      )

      const { session_id } = response.data
      localStorage.setItem('auth_token', session_id)
      setTenantId(String(tenantId))

      // 2. Load the profile
      await fetchProfile()
    } catch (error) {
      setIsLoading(false)
      throw error
    }
  }

  const logout = async () => {
    setIsLoading(true)
    try {
      await httpClient.post('/v1/auth/logout')
    } catch {
      // Ignore network errors on logout to allow clean slate local exit
    } finally {
      localStorage.removeItem('auth_token')
      setEmployee(null)
      setIsLoading(false)
    }
  }

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated: !!employee,
        isLoading,
        employee,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
