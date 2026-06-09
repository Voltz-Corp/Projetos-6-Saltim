import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export interface SupplierOption {
  id: number
  supplier_id: string
  supplier_name: string
  unit_price: number
  discount_percent: number
  min_to_discount: number
  effective_unit_price: number
  delivery_time_days: number
  delay_risk: number
  score: number
  recommended: boolean
  reason?: string | null
}

export interface PurchasePlanItem {
  id: number
  ingredient_id: string
  ingredient_name: string
  category?: string | null
  unit?: string | null
  current_qty: number
  avg_daily_usage: number
  forecast_qty: number
  in_transit_qty: number
  recommended_qty: number
  approved_qty: number
  selected_supplier_id?: string | null
  selected_supplier_name?: string | null
  estimated_unit_price: number
  estimated_total: number
  coverage_days: number
  criticality: string
  justification?: string | null
  note?: string | null
  options: SupplierOption[]
}

export interface SupplierQuote {
  id: number
  supplier_id: string
  supplier_name: string
  email?: string | null
  channel: string
  status: string
  sent_at?: string | null
  responded_at?: string | null
  approved_at?: string | null
  total_estimated: number
  notes?: string | null
}

export interface PurchasePlan {
  id: number
  created_at: string
  updated_at: string
  status: string
  source: string
  horizon_days: number
  date_from?: string | null
  date_to?: string | null
  contagem_id?: number | null
  total_estimated: number
  approved_total: number
  critical_items_count: number
  avg_coverage_days: number
  savings_potential: number
  items: PurchasePlanItem[]
  quotes: SupplierQuote[]
}

export interface PurchasePlanSimulation {
  total_estimated: number
  approved_total: number
  projected_coverage_days: number
  rupture_risk_items: number
  critical_items_count: number
  savings_potential: number
  notes: string[]
}

export interface GeneratePurchasePlanPayload {
  contagem_id?: number
  horizon_days?: number
  date_from?: string
  date_to?: string
}

export interface UpdatePurchasePlanItemPayload {
  planId: number
  ingredientId: string
  approved_qty?: number
  selected_supplier_id?: string | null
  note?: string
}

export interface SimulatePurchasePlanPayload {
  planId: number
  items?: Array<{
    ingredient_id: string
    approved_qty: number
    selected_supplier_id?: string | null
  }>
}

async function readError(response: Response, fallback: string) {
  try {
    const body = await response.json()
    return body.detail || fallback
  } catch {
    return fallback
  }
}

export function useLatestPurchasePlan() {
  return useQuery({
    queryKey: ['purchase-plan-latest'],
    queryFn: async (): Promise<PurchasePlan | null> => {
      const response = await fetch(`${API_URL}/api/compras/planos/latest`)
      if (!response.ok) throw new Error('Falha ao carregar plano de compra')
      return response.json()
    },
    staleTime: 20_000,
  })
}

export function usePurchasePlan(planId?: number) {
  return useQuery({
    queryKey: ['purchase-plan', planId],
    queryFn: async (): Promise<PurchasePlan> => {
      const response = await fetch(`${API_URL}/api/compras/planos/${planId}`)
      if (!response.ok) throw new Error('Falha ao carregar plano de compra')
      return response.json()
    },
    enabled: Boolean(planId),
    staleTime: 20_000,
  })
}

export function useGeneratePurchasePlan() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: GeneratePurchasePlanPayload = {}): Promise<PurchasePlan> => {
      const response = await fetch(`${API_URL}/api/compras/planos/gerar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!response.ok) throw new Error(await readError(response, 'Falha ao gerar plano'))
      return response.json()
    },
    onSuccess: data => {
      queryClient.setQueryData(['purchase-plan-latest'], data)
      queryClient.setQueryData(['purchase-plan', data.id], data)
    },
  })
}

export function useUpdatePurchasePlanItem() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      planId,
      ingredientId,
      ...payload
    }: UpdatePurchasePlanItemPayload): Promise<PurchasePlan> => {
      const response = await fetch(
        `${API_URL}/api/compras/planos/${planId}/items/${ingredientId}`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        },
      )
      if (!response.ok) throw new Error(await readError(response, 'Falha ao atualizar item'))
      return response.json()
    },
    onSuccess: data => {
      queryClient.setQueryData(['purchase-plan-latest'], data)
      queryClient.setQueryData(['purchase-plan', data.id], data)
    },
  })
}

export function useSendPurchaseQuotes() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (planId: number): Promise<PurchasePlan> => {
      const response = await fetch(`${API_URL}/api/compras/planos/${planId}/cotacoes/enviar`, {
        method: 'POST',
      })
      if (!response.ok) throw new Error(await readError(response, 'Falha ao enviar cotacoes'))
      return response.json()
    },
    onSuccess: data => {
      queryClient.setQueryData(['purchase-plan-latest'], data)
      queryClient.setQueryData(['purchase-plan', data.id], data)
    },
  })
}

export function useApprovePurchasePlan() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (planId: number) => {
      const response = await fetch(`${API_URL}/api/compras/planos/${planId}/aprovar`, {
        method: 'POST',
      })
      if (!response.ok) throw new Error(await readError(response, 'Falha ao aprovar plano'))
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['purchase-plan-latest'] })
      queryClient.invalidateQueries({ queryKey: ['purchase-plan'] })
      queryClient.invalidateQueries({ queryKey: ['pedidos'] })
      queryClient.invalidateQueries({ queryKey: ['pedidos-em-transito'] })
    },
  })
}

export function useSimulatePurchasePlan() {
  return useMutation({
    mutationFn: async ({ planId, items = [] }: SimulatePurchasePlanPayload): Promise<PurchasePlanSimulation> => {
      const response = await fetch(`${API_URL}/api/compras/planos/${planId}/simular`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items }),
      })
      if (!response.ok) throw new Error(await readError(response, 'Falha ao simular plano'))
      return response.json()
    },
  })
}
