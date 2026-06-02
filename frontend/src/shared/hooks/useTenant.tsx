import { createContext, type ReactNode, useContext, useEffect, useState } from 'react'

interface TenantContextType {
  tenantId: string | null
  setTenantId: (id: string) => void
}

const TenantContext = createContext<TenantContextType | undefined>(undefined)

export function TenantProvider({ children }: { children: ReactNode }) {
  const [tenantId, setTenantIdState] = useState<string | null>(() => {
    // 1. Check URL query params first
    const params = new URLSearchParams(window.location.search)
    const urlTenant = params.get('tenant')
    if (urlTenant) {
      localStorage.setItem('tenant_id', urlTenant)
      return urlTenant
    }

    // 2. Check LocalStorage
    return localStorage.getItem('tenant_id')
  })

  const setTenantId = (id: string) => {
    localStorage.setItem('tenant_id', id)
    setTenantIdState(id)
  }

  // Handle re-synchronization of tenant parameter in search URL if present
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const urlTenant = params.get('tenant')
    if (urlTenant && urlTenant !== tenantId) {
      setTenantIdState(urlTenant)
    }
  }, [tenantId])

  return (
    <TenantContext.Provider value={{ tenantId, setTenantId }}>{children}</TenantContext.Provider>
  )
}

export function useTenant() {
  const context = useContext(TenantContext)
  if (!context) {
    throw new Error('useTenant must be used within a TenantProvider')
  }
  return context
}
