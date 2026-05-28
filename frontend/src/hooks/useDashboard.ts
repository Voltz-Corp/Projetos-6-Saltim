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
  items: DashboardKpi[]
}

export interface DashboardKpi {
  id: 'ingredients' | 'coverage' | 'top_recipe' | 'critical_ingredient'
  label: string
  value: string
  detail: string
  trend_value?: number | null
  trend_label: string
  trend_direction: 'up' | 'down' | 'neutral'
}

export interface DashboardIngredientFilter {
  id: string
  name: string
  category_id: string
  category: string
}

export interface DashboardHolidayFilter {
  date: string
  name: string
  type: string
}

export interface DashboardMonthFilter {
  key: string
  label: string
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
  bottom_stock_categories_by_unit: DashboardUnitCategoryGroup[]
  top_output_products_by_unit: DashboardUnitRankGroup[]
  bottom_output_products_by_unit: DashboardUnitRankGroup[]
  top_output_categories_by_unit: DashboardUnitCategoryGroup[]
  bottom_output_categories_by_unit: DashboardUnitCategoryGroup[]
  alerts: DashboardAlert[]
  filters: {
    categories: DashboardCategoryItem[]
    ingredients: DashboardIngredientFilter[]
    holidays: DashboardHolidayFilter[]
    months: DashboardMonthFilter[]
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
  categoryIds?: string[]
  eventTypes?: string[]
  monthKeys?: string[]
  years?: string[]
  months?: string[]
  dateFrom?: string
  dateTo?: string
  allPeriod?: boolean
}

export interface DashboardRecipeItem {
  id: string
  name: string
  quantity: number
  revenue: number
}

export interface DashboardNamedMetric {
  key: string
  label: string
  value: number
}

export interface DashboardRevenueSummary {
  monthly: DashboardNamedMetric[]
  quarterly: DashboardNamedMetric[]
}

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`)
  if (!res.ok) throw new Error('Falha ao carregar dados do dashboard')
  return res.json()
}

function appendGlobalFilters(params: URLSearchParams, filters?: StockHistoryFilters) {
  if (!filters) return
  if (filters.days && !filters.allPeriod) params.set('days', String(filters.days))
  if (filters.allPeriod) params.set('all_period', 'true')
  if (filters.dateFrom) params.set('date_from', filters.dateFrom)
  if (filters.dateTo) params.set('date_to', filters.dateTo)
  filters.categoryIds?.forEach(value => params.append('category_ids', value))
  filters.eventTypes?.forEach(value => params.append('event_types', value))
  filters.monthKeys?.forEach(value => params.append('month_keys', value))
  filters.years?.forEach(value => params.append('years', value))
  filters.months?.forEach(value => params.append('month_numbers', value))
}

export function useDashboard(filters?: StockHistoryFilters) {
  const params = new URLSearchParams()
  appendGlobalFilters(params, filters)
  const query = params.toString()

  return useQuery({
    queryKey: ['dashboard', filters],
    queryFn: () => fetchJson<DashboardResponse>(`/api/dashboard${query ? `?${query}` : ''}`),
    staleTime: 30_000,
  })
}

export function useStockHistory(filters: StockHistoryFilters) {
  const params = new URLSearchParams()
  if (filters.ingredientId) params.set('ingredient_id', filters.ingredientId)
  if (filters.categoryId && !filters.ingredientId) params.set('category_id', filters.categoryId)
  appendGlobalFilters(params, filters)

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
  appendGlobalFilters(params, filters)

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
  appendGlobalFilters(params, filters)

  return useQuery({
    queryKey: ['dashboard-recipe-ranking', filters],
    queryFn: () => fetchJson<DashboardRecipeItem[]>(`/api/dashboard/receitas-ranking?${params}`),
    staleTime: 30_000,
    placeholderData: previous => previous,
  })
}

export function useRevenueSummary(months = 12, filters?: StockHistoryFilters) {
  const params = new URLSearchParams()
  params.set('months', String(months))
  appendGlobalFilters(params, filters)

  return useQuery({
    queryKey: ['dashboard-revenue-summary', months, filters],
    queryFn: () => fetchJson<DashboardRevenueSummary>(`/api/dashboard/faturamento-resumo?${params}`),
    staleTime: 30_000,
    placeholderData: previous => previous,
  })
}

export function useWeekdayOrders(days = 90, filters?: StockHistoryFilters) {
  const params = new URLSearchParams()
  params.set('days', String(days))
  appendGlobalFilters(params, filters)

  return useQuery({
    queryKey: ['dashboard-weekday-orders', days, filters],
    queryFn: () => fetchJson<DashboardNamedMetric[]>(`/api/dashboard/pedidos-semana?${params}`),
    staleTime: 30_000,
    placeholderData: previous => previous,
  })
}
