import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export interface PedidoGroup {
  group_key: string
  supplier_id: string
  supplier_name: string
  order_date: string
  expected_date: string
  ingredients_count: number
  items_qty: number
  total_value: number
  status: string
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
  items: PedidoGroup[]
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
  group_key?: string | null
  supplier_id: string
  supplier_name: string
  order_date: string
  expected_date: string
  status: string
  items_qty: number
  total_value: number
  items: PedidoDetailItem[]
}

export interface PedidoRecommendationRequest {
  items: Array<{
    ingredient_id: string
    qty: number
  }>
}

export interface SupplierOption {
  supplier_id: string
  supplier_name: string
  unit_price: number
  discount_percent: number
  min_to_discount: number
  discount_applied: boolean
  effective_unit_price: number
  total_value: number
  delivery_time_days: number
  expected_date: string
  detractors: string[]
  recommended: boolean
}

export interface PedidoRecommendationItem {
  ingredient_id: string
  ingredient_name: string
  category: string
  unit: string
  qty: number
  recommended_supplier_id?: string | null
  options: SupplierOption[]
}

export interface RecommendedOrderGroup {
  supplier_id: string
  supplier_name: string
  expected_date: string
  total_value: number
  items: Array<{
    ingredient_id: string
    ingredient_name: string
    qty: number
    unit: string
    total_value: number
    expected_date: string
  }>
}

export interface PedidoRecommendationResponse {
  items: PedidoRecommendationItem[]
  groups: RecommendedOrderGroup[]
}

export interface PedidoCreateRequest {
  items: Array<{
    ingredient_id: string
    qty: number
    supplier_id: string
  }>
}

export interface PedidoCreateResponse {
  groups: PedidoGroup[]
  created: number
  updated: number
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
    queryFn: async (): Promise<PedidoGroup[]> => {
      const response = await fetch(`${API_URL}/api/pedidos/em-transito?${params}`)
      if (!response.ok) throw new Error('Falha ao carregar pedidos em trânsito')
      return response.json()
    },
    staleTime: 15_000,
    placeholderData: previous => previous,
  })
}

export function usePedidoGroupDetail(supplierId: string, orderDate: string) {
  return useQuery({
    queryKey: ['pedido-grupo', supplierId, orderDate],
    queryFn: async (): Promise<PedidoDetail> => {
      const response = await fetch(
        `${API_URL}/api/pedidos/grupos/${supplierId}/${orderDate}`,
      )
      if (!response.ok) throw new Error('Falha ao carregar pedido')
      return response.json()
    },
    enabled: Boolean(supplierId && orderDate),
    staleTime: 30_000,
  })
}

export function usePedidoRecommendation() {
  return useMutation({
    mutationFn: async (
      payload: PedidoRecommendationRequest,
    ): Promise<PedidoRecommendationResponse> => {
      const response = await fetch(`${API_URL}/api/pedidos/recomendacao`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!response.ok) throw new Error('Falha ao recomendar fornecedores')
      return response.json()
    },
  })
}

export function useCreatePedido() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (
      payload: PedidoCreateRequest,
    ): Promise<PedidoCreateResponse> => {
      const response = await fetch(`${API_URL}/api/pedidos`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!response.ok) throw new Error('Falha ao criar pedido')
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pedidos'] })
      queryClient.invalidateQueries({ queryKey: ['pedidos-em-transito'] })
    },
  })
}

export function useMarkPedidoGroupDelivered() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      supplierId,
      orderDate,
    }: {
      supplierId: string
      orderDate: string
    }): Promise<PedidoDetail> => {
      const response = await fetch(
        `${API_URL}/api/pedidos/grupos/${supplierId}/${orderDate}/entregar`,
        { method: 'PATCH' },
      )
      if (!response.ok) throw new Error('Falha ao atualizar pedido')
      return response.json()
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['pedidos'] })
      queryClient.invalidateQueries({ queryKey: ['pedidos-em-transito'] })
      queryClient.invalidateQueries({
        queryKey: ['pedido-grupo', variables.supplierId, variables.orderDate],
      })
    },
  })
}
