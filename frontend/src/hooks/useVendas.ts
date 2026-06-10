import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export interface VendaProduto {
  id: string
  name: string
  recipe_type: string
  sale_price: number
  yield_qty?: number | null
  yield_unit?: string | null
  ingredients_count: number
  available: boolean
  max_quantity?: number | null
  stock_warnings: string[]
}

export interface ClienteVenda {
  id: string
  name: string
  document?: string | null
  email?: string | null
  phone?: string | null
  created_at?: string | null
}

export interface VendaItemCreate {
  recipe_id: string
  quantity: number
  unit_price?: number
  discount_value?: number
}

export interface VendaCreateRequest {
  customer_id?: string
  customer?: {
    name: string
    document?: string
    email?: string
    phone?: string
  }
  items: VendaItemCreate[]
  discount_total?: number
  source?: string
  notes?: string
}

export interface MesaVenda {
  numero: number
  status: 'livre' | 'ocupada'
  comanda_id?: string | null
  items_count: number
  items_qty: number
  total: number
  opened_at?: string | null
}

export interface MesasResponse {
  total_mesas: number
  mesas: MesaVenda[]
}

export interface MesaPedido {
  mesa_numero: number
  comanda_id: string
}

export interface VendaItensUpdateRequest {
  items: VendaItemCreate[]
  mesa_numero?: number
  customer_name?: string
  cpf_cliente?: string
  notes?: string
}

export interface VendaFecharRequest {
  payment_method: string
  paid_amount?: number
  cpf_cliente?: string
  customer_name?: string
  notes?: string
}

export interface VendaItem {
  id: string
  recipe_id: string
  recipe_name: string
  quantity: number
  unit_price: number
  discount_value: number
  total_value: number
  venda_historica_id?: string | null
}

export interface VendaDetail {
  id: string
  comanda_id?: string | null
  date_time: string
  customer?: ClienteVenda | null
  customer_name?: string | null
  cpf_cliente?: string | null
  mesa_numero?: number | null
  status: string
  payment_method?: string | null
  subtotal: number
  discount_total: number
  total: number
  source: string
  notes?: string | null
  confirmed_at?: string | null
  canceled_at?: string | null
  items: VendaItem[]
}

export interface VendaListItem {
  id: string
  comanda_id?: string | null
  date_time: string
  customer_name?: string | null
  cpf_cliente?: string | null
  mesa_numero?: number | null
  status: string
  payment_method?: string | null
  items_count: number
  items_qty: number
  total: number
  paid_total: number
}

export interface VendaFilters {
  status?: string
  q?: string
  dateFrom?: string
  dateTo?: string
  page?: number
  pageSize?: number
}

export interface VendasPaginadas {
  items: VendaListItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
  paid_revenue_total: number
}

export interface VendaFechamentoDia {
  date: string
  vendas_dia: number
  is_holiday: number
  is_carnaval_window: number
  is_sao_joao: number
  is_summer: number
  is_promo_day: number
  is_rain_event: number
  is_closure: number
}

async function parseError(response: Response, fallback: string) {
  try {
    const body = await response.json()
    if (typeof body?.detail === 'string') return body.detail
    if (body?.detail?.message) return body.detail.message
  } catch {
    // Keep the generic message.
  }
  return fallback
}

function paramsFromFilters(filters: VendaFilters) {
  const params = new URLSearchParams()
  if (filters.status) params.set('status', filters.status)
  if (filters.q) params.set('q', filters.q)
  if (filters.dateFrom) params.set('date_from', filters.dateFrom)
  if (filters.dateTo) params.set('date_to', filters.dateTo)
  if (filters.page) params.set('page', String(filters.page))
  if (filters.pageSize) params.set('page_size', String(filters.pageSize))
  return params
}

export function useVendaProdutos(q = '') {
  const params = new URLSearchParams()
  if (q) params.set('q', q)

  return useQuery({
    queryKey: ['vendas-produtos', q],
    queryFn: async (): Promise<VendaProduto[]> => {
      const response = await fetch(`${API_URL}/api/vendas/produtos?${params}`)
      if (!response.ok) throw new Error(await parseError(response, 'Falha ao carregar produtos'))
      return response.json()
    },
    staleTime: 30_000,
  })
}

export function useVendas(filters: VendaFilters) {
  const params = paramsFromFilters(filters)

  return useQuery({
    queryKey: ['vendas', filters],
    queryFn: async (): Promise<VendasPaginadas> => {
      const response = await fetch(`${API_URL}/api/vendas?${params}`)
      if (!response.ok) throw new Error(await parseError(response, 'Falha ao carregar vendas'))
      return response.json()
    },
    staleTime: 15_000,
    placeholderData: previous => previous,
  })
}

export function useVendaMesas() {
  return useQuery({
    queryKey: ['vendas-mesas'],
    queryFn: async (): Promise<MesasResponse> => {
      const response = await fetch(`${API_URL}/api/vendas/mesas`)
      if (!response.ok) throw new Error(await parseError(response, 'Falha ao carregar mesas'))
      return response.json()
    },
    staleTime: 10_000,
  })
}

export function useVendaDetail(id?: string) {
  return useQuery({
    queryKey: ['venda', id],
    queryFn: async (): Promise<VendaDetail> => {
      const response = await fetch(`${API_URL}/api/vendas/${id}`)
      if (!response.ok) throw new Error(await parseError(response, 'Falha ao carregar venda'))
      return response.json()
    },
    enabled: Boolean(id),
    staleTime: 30_000,
  })
}

export function useCreateMesaPedido() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (mesaNumero: number): Promise<MesaPedido> => {
      const response = await fetch(`${API_URL}/api/vendas/mesas/${mesaNumero}/pedido`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      })
      if (!response.ok) throw new Error(await parseError(response, 'Falha ao abrir mesa'))
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vendas-mesas'] })
    },
  })
}

export function useUpdateVendaItens() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ id, payload }: { id: string; payload: VendaItensUpdateRequest }): Promise<VendaDetail> => {
      const response = await fetch(`${API_URL}/api/vendas/${id}/itens`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!response.ok) throw new Error(await parseError(response, 'Falha ao salvar itens'))
      return response.json()
    },
    onSuccess: data => {
      queryClient.invalidateQueries({ queryKey: ['vendas'] })
      queryClient.invalidateQueries({ queryKey: ['vendas-mesas'] })
      queryClient.invalidateQueries({ queryKey: ['venda', data.id] })
    },
  })
}

export function useFecharVenda() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ id, payload }: { id: string; payload: VendaFecharRequest }): Promise<VendaDetail> => {
      const response = await fetch(`${API_URL}/api/vendas/${id}/fechar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!response.ok) throw new Error(await parseError(response, 'Falha ao fechar mesa'))
      return response.json()
    },
    onSuccess: data => {
      queryClient.invalidateQueries({ queryKey: ['vendas'] })
      queryClient.invalidateQueries({ queryKey: ['vendas-mesas'] })
      queryClient.invalidateQueries({ queryKey: ['venda', data.id] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}

export function useFecharDiaVendas() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (date?: string): Promise<VendaFechamentoDia> => {
      const params = new URLSearchParams()
      if (date) params.set('date', date)
      const suffix = params.toString() ? `?${params}` : ''
      const response = await fetch(`${API_URL}/api/vendas/fechamento-dia${suffix}`, {
        method: 'POST',
      })
      if (!response.ok) throw new Error(await parseError(response, 'Falha ao fechar o dia'))
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vendas'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}

export function useCancelVenda() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (id: string): Promise<VendaDetail> => {
      const response = await fetch(`${API_URL}/api/vendas/${id}/cancelar`, {
        method: 'PATCH',
      })
      if (!response.ok) throw new Error(await parseError(response, 'Falha ao cancelar venda'))
      return response.json()
    },
    onSuccess: data => {
      queryClient.invalidateQueries({ queryKey: ['vendas'] })
      queryClient.invalidateQueries({ queryKey: ['vendas-mesas'] })
      queryClient.invalidateQueries({ queryKey: ['venda', data.id] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}
