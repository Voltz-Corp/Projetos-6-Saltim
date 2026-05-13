import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type { Category } from '../data/ingredients'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const QUERY_KEY = ['estoque'] as const

// Espelha o schema que a API retorna (snake_case) + aliases camelCase
// para compatibilidade com o restante do front sem precisar alterar cada componente.
export interface StockItem {
  id: number
  name: string
  unit: string
  price: number
  category: Category
  min_qty: number
  current_qty: number
  // aliases camelCase (adicionados no fetch)
  minQty: number
  currentQty: number
}

export type StockStatus = 'Esgotado' | 'Crítico' | 'Atenção' | 'OK'

export function getStockStatus(item: StockItem): StockStatus {
  const qty = item.currentQty
  if (qty <= 0) return 'Esgotado'
  if (qty < item.minQty) return 'Crítico'
  if (qty < item.minQty * 1.5) return 'Atenção'
  return 'OK'
}

async function fetchEstoque(): Promise<StockItem[]> {
  const res = await fetch(`${API_URL}/api/estoque`)
  if (!res.ok) throw new Error('Falha ao carregar estoque')
  const data: Array<Record<string, unknown>> = await res.json()
  // Adiciona aliases camelCase para não precisar alterar os componentes
  return data.map(item => ({
    ...(item as any),
    minQty: item['min_qty'] as number,
    currentQty: item['current_qty'] as number,
  }))
}

export function useEstoque() {
  return useQuery({
    queryKey: QUERY_KEY,
    queryFn: fetchEstoque,
    staleTime: 30_000,
  })
}

export type StockStatusFilter = 'OK' | 'Atenção' | 'Crítico' | 'Esgotado'

export interface EstoqueFiltros {
  category?: string
  status?: StockStatusFilter
  q?: string
  page?: number
  pageSize?: number
}

export interface EstoquePaginado {
  items: StockItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export function useEstoquePaginado(filtros: EstoqueFiltros) {
  const params = new URLSearchParams()
  if (filtros.category) params.set('category', filtros.category)
  if (filtros.status) params.set('status', filtros.status)
  if (filtros.q) params.set('q', filtros.q)
  if (filtros.page) params.set('page', String(filtros.page))
  if (filtros.pageSize) params.set('page_size', String(filtros.pageSize))

  return useQuery({
    queryKey: ['estoque-paginado', filtros],
    queryFn: async (): Promise<EstoquePaginado> => {
      const res = await fetch(`${API_URL}/api/estoque/paginado?${params}`)
      if (!res.ok) throw new Error('Falha ao carregar estoque')
      const data = await res.json()
      return {
        ...data,
        items: data.items.map((item: Record<string, unknown>) => ({
          ...(item as any),
          minQty: item['min_qty'] as number,
          currentQty: item['current_qty'] as number,
        })),
      }
    },
    staleTime: 15_000,
    placeholderData: (prev) => prev,
  })
}

export interface AtualizacaoIngrediente {
  name?: string
  unit?: string
  price?: number
  category?: string
  min_qty?: number
}

export function useAtualizarIngrediente() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, ...dados }: AtualizacaoIngrediente & { id: number }): Promise<StockItem> => {
      const res = await fetch(`${API_URL}/api/ingredientes/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(dados),
      })
      if (!res.ok) throw new Error('Falha ao atualizar ingrediente')
      const item = await res.json()
      return { ...item, minQty: item.min_qty, currentQty: item.current_qty }
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEY })
    },
  })
}

export function useAtualizarEstoque() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (updates: Map<number, number>) => {
      const body = {
        updates: Array.from(updates.entries()).map(([id, new_qty]) => ({ id, new_qty })),
        session_label: 'contagem',
      }
      const res = await fetch(`${API_URL}/api/estoque`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) throw new Error('Falha ao salvar estoque')
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEY })
    },
  })
}
