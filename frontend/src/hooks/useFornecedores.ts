import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export interface Fornecedor {
  id: string
  name: string
  cnpj?: string | null
  email?: string | null
  phone?: string | null
  avg_delivery_time?: number | null
  item_count?: number
  avg_price?: number | null
}

export interface FornecedorKpis {
  supplier_count: number
  avg_delivery_time: number
  avg_items_per_supplier: number
  best_value_supplier_id?: string | null
  best_value_supplier_name?: string | null
  best_value_detail: string
}

export interface FornecedoresResponse {
  kpis: FornecedorKpis
  items: Fornecedor[]
}

export interface FornecedorProduct {
  ingredient_id: string
  name: string
  category: string
  current_qty: number
  unit: string
  unit_price: number
}

export interface FornecedorOrder {
  id: string
  order_date: string
  items_qty: number
  total_value: number
  status: string
}

export interface FornecedorProfile {
  supplier: Fornecedor
  kpis: {
    avg_lead_time: number
    orders_count: number
    delivery_rate: number
  }
  products: FornecedorProduct[]
  orders: FornecedorOrder[]
}

export interface FornecedorIngredientPayload {
  ingredient_id: string
  price: number
  discount_percent?: number
  min_to_discount?: number
}

export interface FornecedorCreatePayload {
  name: string
  cnpj?: string
  email?: string
  phone?: string
  avg_delivery_time?: number
  ingredients: FornecedorIngredientPayload[]
}

export function useFornecedores() {
  return useQuery({
    queryKey: ['fornecedores'],
    queryFn: async () => {
      const response = await fetch(`${API_URL}/api/fornecedores`)
      if (!response.ok) throw new Error('Falha ao carregar fornecedores')
      return response.json() as Promise<FornecedoresResponse>
    },
    staleTime: 30_000,
  })
}

export function useCreateFornecedor() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: FornecedorCreatePayload) => {
      const response = await fetch(`${API_URL}/api/fornecedores`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!response.ok) throw new Error('Falha ao cadastrar fornecedor')
      return response.json() as Promise<Fornecedor>
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fornecedores'] })
    },
  })
}

export function useFornecedorProfile(id: string) {
  return useQuery({
    queryKey: ['fornecedor', id],
    queryFn: async () => {
      const response = await fetch(`${API_URL}/api/fornecedores/${id}`)
      if (!response.ok) throw new Error('Falha ao carregar fornecedor')
      return response.json() as Promise<FornecedorProfile>
    },
    enabled: Boolean(id),
    staleTime: 30_000,
  })
}
