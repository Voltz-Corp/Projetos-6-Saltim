import { useQuery } from '@tanstack/react-query'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export interface CriticidadeRun {
  id: number | null
  reference_date: string | null
  generated_at: string | null
  status: 'success' | 'pending_contagem' | 'failed' | 'no_report' | string
  contagem_id: number | null
  contagem_status: string | null
  model_name: string | null
  model_uri: string | null
  model_run_id: string | null
  total_items: number
  ok_count: number
  alert_count: number
  alert_rate: number
  metrics: Record<string, unknown>
  stability: Record<string, unknown>
  error_message: string | null
}

export interface CriticidadeItem {
  ingredient_id: string
  ingredient_name: string
  category_id: string | null
  category: string | null
  unit: string | null
  estoque_atual: number
  stock_position: number
  baseline_threshold: number
  cobertura_estoque_pct: number
  limiar_alerta_predito_pct: number
  limiar_critico_predito_pct: number
  criticidade_predita: string
  necessita_compra: boolean
  score_alerta_compra: number
  rank_position: number
}

export interface CriticidadeCategory {
  category: string
  total_items: number
  ok_count: number
  alert_count: number
  alert_rate: number
}

export interface CriticidadeReport {
  run: CriticidadeRun
  distribution: Array<{ status: string; count: number; rate: number }>
  categories: CriticidadeCategory[]
  critical_items: CriticidadeItem[]
  examples_critical: CriticidadeItem[]
  examples_ok: CriticidadeItem[]
}

export function useCriticidadeReport() {
  return useQuery({
    queryKey: ['criticidade-report-latest'],
    queryFn: async (): Promise<CriticidadeReport> => {
      const response = await fetch(`${API_URL}/api/ml/criticidade/relatorio/latest`)
      if (!response.ok) throw new Error('Falha ao carregar relatório de criticidade')
      return response.json()
    },
    staleTime: 30_000,
  })
}
