import { useQuery } from '@tanstack/react-query'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export interface Pedido {
  id: string
  supplier_id: string
  supplier_name: string
  ingredient_id: string
  ingredient_name: string
  order_date: string
  items_qty: number
  total_value: number
  status: string
  expected_date: string
}

export interface PedidoFilters {
  status?: string
  supplierId?: string
  dateFrom?: string
  dateTo?: string
  page?: number
  pageSize?: number
}

export interface PedidosPaginados {
  items: Pedido[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface PedidoDetailItem {
  ingredient_id: string
  ingredient_name: string
  category: string
  unit: string
  qty: number
  unit_price: number
  total_value: number
}

export interface PedidoDetail {
  id: string
  supplier_id: string
  supplier_name: string
  order_date: string
  expected_date: string
  status: string
  items_qty: number
  total_value: number
  items: PedidoDetailItem[]
}

function paramsFromFilters(filters: PedidoFilters, includePagination = true) {
  const params = new URLSearchParams()
  if (filters.status) params.set('status', filters.status)
  if (filters.supplierId) params.set('supplier_id', filters.supplierId)
  if (filters.dateFrom) params.set('date_from', filters.dateFrom)
  if (filters.dateTo) params.set('date_to', filters.dateTo)
  if (includePagination) {
    if (filters.page) params.set('page', String(filters.page))
    if (filters.pageSize) params.set('page_size', String(filters.pageSize))
  }
  return params
}

export function usePedidos(filters: PedidoFilters) {
  const params = paramsFromFilters(filters)

  return useQuery({
    queryKey: ['pedidos', filters],
    queryFn: async (): Promise<PedidosPaginados> => {
      const response = await fetch(`${API_URL}/api/pedidos?${params}`)
      if (!response.ok) throw new Error('Falha ao carregar pedidos')
      return response.json()
    },
    staleTime: 15_000,
    placeholderData: previous => previous,
  })
}

export function usePedidosEmTransito(filters: PedidoFilters) {
  const params = paramsFromFilters(filters, false)

  return useQuery({
    queryKey: ['pedidos-em-transito', filters],
    queryFn: async (): Promise<Pedido[]> => {
      const response = await fetch(`${API_URL}/api/pedidos/em-transito?${params}`)
      if (!response.ok) throw new Error('Falha ao carregar pedidos em trânsito')
      return response.json()
    },
    staleTime: 15_000,
    placeholderData: previous => previous,
  })
}

export function usePedidoDetail(id: string) {
  return useQuery({
    queryKey: ['pedido', id],
    queryFn: async (): Promise<PedidoDetail> => {
      const response = await fetch(`${API_URL}/api/pedidos/${id}`)
      if (!response.ok) throw new Error('Falha ao carregar pedido')
      return response.json()
    },
    enabled: Boolean(id),
    staleTime: 30_000,
  })
}
