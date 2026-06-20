import { httpClient } from '@/shared/lib/http_client'

export interface Tenant {
  id: number
  name: string
  plan_type: 'BASIC' | 'PRO' | 'PLUS'
  is_active: boolean
}

export interface Manager {
  id: number
  name: string
  email: string
  tenant_id: number
  is_active: boolean
}

export interface AnalyticsItem {
  _id: string | number
  total_revenue: number
}

export const getTenants = (): Promise<Tenant[]> =>
  httpClient.get('/v1/admin/tenants').then((res) => res.data)
export const createTenant = (data: { name: string; plan_type: string }): Promise<Tenant> =>
  httpClient.post('/v1/admin/tenants', data).then((res) => res.data)
export const deleteTenant = (tenantId: number): Promise<void> =>
  httpClient.delete(`/v1/admin/tenants/${tenantId}`).then((res) => res.data)
export const getGlobalAnalytics = (params: { limit: number }): Promise<AnalyticsItem[]> =>
  httpClient.get('/v1/admin/analytics/global', { params }).then((res) => res.data)
export const exportAnalytics = (tenantId?: string): Promise<{ data: Blob }> =>
  httpClient.get('/v1/admin/analytics/export', {
    params: { tenant_id: tenantId },
    responseType: 'blob',
  })

export const getManagers = (): Promise<Manager[]> =>
  httpClient.get('/v1/admin/managers').then((res) => res.data)
export const createManager = (data: {
  name: string
  email: string
  password: string
  tenant_id: number
}): Promise<Manager> => httpClient.post('/v1/admin/managers', data).then((res) => res.data)
export const deleteManager = (employeeId: number): Promise<void> =>
  httpClient.delete(`/v1/admin/managers/${employeeId}`).then((res) => res.data)
