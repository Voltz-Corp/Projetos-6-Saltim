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
