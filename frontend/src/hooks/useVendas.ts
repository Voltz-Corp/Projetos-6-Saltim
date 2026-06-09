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

export interface VendaPagamentoCreate {
  method: string
  amount: number
  status?: string
  change_amount?: number
  external_reference?: string
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
  payments?: VendaPagamentoCreate[]
  discount_total?: number
  source?: string
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

export interface VendaPagamento {
  id: string
  method: string
  amount: number
  status: string
  paid_at?: string | null
  change_amount: number
  external_reference?: string | null
}

export interface VendaFiscalDocument {
  id: string
  venda_id: string
  document_type: string
  status: string
  provider?: string | null
  access_key?: string | null
  protocol?: string | null
  issued_at?: string | null
  cancelled_at?: string | null
  payload?: Record<string, unknown> | null
  error_message?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export interface VendaDetail {
  id: string
  date_time: string
  customer?: ClienteVenda | null
  status: string
  fiscal_status: string
  subtotal: number
  discount_total: number
  total: number
  source: string
  notes?: string | null
  confirmed_at?: string | null
  canceled_at?: string | null
  items: VendaItem[]
  payments: VendaPagamento[]
  fiscal_document?: VendaFiscalDocument | null
}

export interface VendaListItem {
  id: string
  date_time: string
  customer_name?: string | null
  status: string
  fiscal_status: string
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

export function useCreateAndConfirmVenda() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: VendaCreateRequest): Promise<VendaDetail> => {
      const createResponse = await fetch(`${API_URL}/api/vendas`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...payload, payments: [] }),
      })
      if (!createResponse.ok) {
        throw new Error(await parseError(createResponse, 'Falha ao criar venda'))
      }
      const created: VendaDetail = await createResponse.json()
      const confirmResponse = await fetch(`${API_URL}/api/vendas/${created.id}/confirmar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ payments: payload.payments ?? [] }),
      })
      if (!confirmResponse.ok) {
        throw new Error(await parseError(confirmResponse, 'Falha ao confirmar venda'))
      }
      return confirmResponse.json()
    },
    onSuccess: data => {
      queryClient.invalidateQueries({ queryKey: ['vendas'] })
      queryClient.invalidateQueries({ queryKey: ['venda', data.id] })
      queryClient.invalidateQueries({ queryKey: ['vendas-produtos'] })
      queryClient.invalidateQueries({ queryKey: ['estoque'] })
      queryClient.invalidateQueries({ queryKey: ['estoque-paginado'] })
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
      queryClient.invalidateQueries({ queryKey: ['venda', data.id] })
      queryClient.invalidateQueries({ queryKey: ['vendas-produtos'] })
      queryClient.invalidateQueries({ queryKey: ['estoque'] })
      queryClient.invalidateQueries({ queryKey: ['estoque-paginado'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}
