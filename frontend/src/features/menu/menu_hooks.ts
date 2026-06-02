import { useQuery } from '@tanstack/react-query'
import { httpClient } from '@/shared/lib/http_client'

export interface MenuItem {
  id: number
  name: string
  description: string
  category: string
  image_url: string | null
  is_available: boolean
  // Under order items, there's station_type_cpy which maps to backend KDS routing.
  // We can include a generic helper/lookup for station types if needed,
  // or fetch it from the API if present (FastAPI schema defines the station_type).
}

export interface Menu {
  id: number
  name: string
  description: string
  is_active: boolean
  items: MenuItem[]
}

export function useActiveMenu() {
  return useQuery<Menu | null>({
    queryKey: ['active-menu'],
    queryFn: async () => {
      const response = await httpClient.get<Menu[]>('/menu')
      // Find the active menu for this tenant
      const active = response.data.find((m) => m.is_active)
      return active || null
    },
  })
}
