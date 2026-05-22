import { useQuery } from '@tanstack/react-query'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export interface DashboardRankItem {
  id: string
  name: string
  value: number
  unit?: string | null
  category?: string | null
}

export interface DashboardCategoryItem {
  id: string
  name: string
  value: number
  unit?: string | null
}

export interface DashboardUnitRankGroup {
  unit: string
  items: DashboardRankItem[]
}

export interface DashboardUnitCategoryGroup {
  unit: string
  items: DashboardCategoryItem[]
}

export interface DashboardCards {
  total_items: number
  total_stock_qty: number
  top_categories_by_unit: DashboardCategoryItem[]
  bottom_categories_by_unit: DashboardCategoryItem[]
  top_products_by_unit: DashboardRankItem[]
  bottom_products_by_unit: DashboardRankItem[]
}

export interface DashboardIngredientFilter {
  id: string
  name: string
  category_id: string
  category: string
}

export interface DashboardAlert {
  ingredient_id: string
  name: string
  category: string
  unit: string
  current_qty: number
  avg_daily_output: number
  coverage_days: number
  suggested_qty: number
  severity: 'Crítico' | 'Atenção' | 'Monitorar'
}

export interface DashboardResponse {
  cards: DashboardCards
  top_stock_products_by_unit: DashboardUnitRankGroup[]
  bottom_stock_products_by_unit: DashboardUnitRankGroup[]
  top_stock_categories_by_unit: DashboardUnitCategoryGroup[]
  top_output_products: DashboardRankItem[]
  bottom_output_products: DashboardRankItem[]
  top_output_categories: DashboardCategoryItem[]
  bottom_output_categories: DashboardCategoryItem[]
  alerts: DashboardAlert[]
  filters: {
    categories: DashboardCategoryItem[]
    ingredients: DashboardIngredientFilter[]
  }
}

export interface StockHistoryPoint {
  date: string
  value: number
}

export interface StockHistoryFilters {
  ingredientId?: string
  categoryId?: string
  days?: number
}

export interface DashboardRecipeItem {
  id: string
  name: string
  quantity: number
  revenue: number
}

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`)
  if (!res.ok) throw new Error('Falha ao carregar dados do dashboard')
  return res.json()
}

export function useDashboard() {
  return useQuery({
    queryKey: ['dashboard'],
    queryFn: () => fetchJson<DashboardResponse>('/api/dashboard'),
    staleTime: 30_000,
  })
}

export function useStockHistory(filters: StockHistoryFilters) {
  const params = new URLSearchParams()
  if (filters.ingredientId) params.set('ingredient_id', filters.ingredientId)
  if (filters.categoryId && !filters.ingredientId) params.set('category_id', filters.categoryId)
  if (filters.days) params.set('days', String(filters.days))

  return useQuery({
    queryKey: ['dashboard-stock-history', filters],
    queryFn: () => fetchJson<StockHistoryPoint[]>(`/api/dashboard/estoque-historico?${params}`),
    staleTime: 30_000,
    placeholderData: previous => previous,
  })
}

export function useSalesHistory(filters: StockHistoryFilters) {
  const params = new URLSearchParams()
  if (filters.ingredientId) params.set('ingredient_id', filters.ingredientId)
  if (filters.categoryId && !filters.ingredientId) params.set('category_id', filters.categoryId)
  if (filters.days) params.set('days', String(filters.days))

  return useQuery({
    queryKey: ['dashboard-sales-history', filters],
    queryFn: () => fetchJson<StockHistoryPoint[]>(`/api/dashboard/vendas-historico?${params}`),
    staleTime: 30_000,
    placeholderData: previous => previous,
  })
}

export function useRecipeRanking(filters: StockHistoryFilters) {
  const params = new URLSearchParams()
  if (filters.ingredientId) params.set('ingredient_id', filters.ingredientId)
  if (filters.categoryId && !filters.ingredientId) params.set('category_id', filters.categoryId)
  if (filters.days) params.set('days', String(filters.days))

  return useQuery({
    queryKey: ['dashboard-recipe-ranking', filters],
    queryFn: () => fetchJson<DashboardRecipeItem[]>(`/api/dashboard/receitas-ranking?${params}`),
    staleTime: 30_000,
    placeholderData: previous => previous,
  })
}
