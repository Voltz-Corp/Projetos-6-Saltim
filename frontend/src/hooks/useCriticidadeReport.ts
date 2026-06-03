import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

function todayRecifeISO() {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Recife',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(new Date())
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]))
  return `${values.year}-${values.month}-${values.day}`
}

function emptyTodayReport(referenceDate: string): CriticidadeReport {
  return {
    run: {
      id: null,
      reference_date: referenceDate,
      generated_at: null,
      status: 'no_report',
      contagem_id: null,
      contagem_status: null,
      model_name: 'XGBoost Regressor',
      model_uri: null,
      model_run_id: null,
      total_items: 0,
      ok_count: 0,
      alert_count: 0,
      alert_rate: 0,
      metrics: {},
      stability: {},
      error_message: 'Nenhum relatório de criticidade foi gerado para hoje.',
    },
    distribution: [],
    categories: [],
    critical_items: [],
    zero_items: [],
    examples_critical: [],
    examples_ok: [],
  }
}

function normalizeTodayReport(report: CriticidadeReport, referenceDate: string) {
  if (report.run?.reference_date === referenceDate) return report
  return emptyTodayReport(referenceDate)
}

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
  zero_items: CriticidadeItem[]
  examples_critical: CriticidadeItem[]
  examples_ok: CriticidadeItem[]
}

export interface CriticidadeJobStatus {
  dia: string
  status: 'running' | 'pending' | 'success' | 'failed'
  inicio_em: string | null
  fim_em: string | null
  atualizado_em: string | null
  error_message: string | null
}

export function useCriticidadeReport() {
  const referenceDate = todayRecifeISO()
  return useQuery({
    queryKey: ['criticidade-report-latest', referenceDate],
    queryFn: async (): Promise<CriticidadeReport> => {
      const response = await fetch(
        `${API_URL}/api/ml/criticidade/relatorio/latest?reference_date=${referenceDate}`,
        { cache: 'no-store' },
      )
      if (!response.ok) throw new Error('Falha ao carregar relatório de criticidade')
      return normalizeTodayReport(await response.json(), referenceDate)
    },
    staleTime: 0,
  })
}

export function useCriticidadeJobStatus() {
  const referenceDate = todayRecifeISO()
  const qc = useQueryClient()
  return useQuery({
    queryKey: ['criticidade-job-status', referenceDate],
    queryFn: async (): Promise<CriticidadeJobStatus> => {
      const response = await fetch(`${API_URL}/api/ml/criticidade/job-status/latest`, {
        cache: 'no-store',
      })
      if (!response.ok) throw new Error('Falha ao carregar status do job')
      const status = (await response.json()) as CriticidadeJobStatus
      if (status.dia !== referenceDate) {
        return {
          dia: referenceDate,
          status: 'pending',
          inicio_em: null,
          fim_em: null,
          atualizado_em: null,
          error_message: 'Nenhuma execução registrada para hoje.',
        }
      }
      if (status.status === 'success' || status.status === 'failed' || status.status === 'pending') {
        qc.invalidateQueries({ queryKey: ['criticidade-report-latest', referenceDate] })
      }
      return status
    },
    staleTime: 0,
    refetchInterval: (query) => (query.state.data?.status === 'running' ? 3_000 : false),
  })
}

export function useRunCriticidadeReport() {
  const qc = useQueryClient()
  const referenceDate = todayRecifeISO()
  return useMutation({
    onMutate: () => {
      qc.setQueryData(['criticidade-job-status', referenceDate], {
        dia: referenceDate,
        status: 'running',
        inicio_em: new Date().toISOString(),
        fim_em: null,
        atualizado_em: new Date().toISOString(),
        error_message: null,
      } satisfies CriticidadeJobStatus)
    },
    mutationFn: async (): Promise<CriticidadeReport> => {
      const response = await fetch(`${API_URL}/api/ml/criticidade/relatorio/run`, {
        method: 'POST',
        cache: 'no-store',
      })
      if (!response.ok) throw new Error('Falha ao rodar o modelo de criticidade')
      return normalizeTodayReport(await response.json(), referenceDate)
    },
    onSuccess: (report) => {
      qc.setQueryData(['criticidade-report-latest', referenceDate], report)
      qc.invalidateQueries({ queryKey: ['criticidade-report-latest', referenceDate] })
      qc.invalidateQueries({ queryKey: ['criticidade-job-status', referenceDate] })
      qc.invalidateQueries({ queryKey: ['estoque'] })
      qc.invalidateQueries({ queryKey: ['estoque-paginado'] })
    },
    onError: () => {
      qc.invalidateQueries({ queryKey: ['criticidade-job-status', referenceDate] })
    },
  })
}
