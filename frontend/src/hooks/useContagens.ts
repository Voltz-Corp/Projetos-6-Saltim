import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { setContagemSession } from './useContagem'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export type ContagemStatus = 'em_andamento' | 'finalizada'
export type ContagemItemStatus = 'nao_contado' | 'sem_alteracao' | 'alterado'

export interface ContagemBase {
  id: number
  label: string
  status: ContagemStatus
  estoque_snapshot_data: string | null
  criada_em: string
  finalizada_em: string | null
}

export interface ContagemResumo extends ContagemBase {
  total_itens: number
  itens_contados: number
  itens_alterados: number
  itens_sem_alteracao: number
  itens_nao_contados: number
}

export interface ContagemDetalheItem {
  ingrediente_id: string
  ingrediente_nome: string
  unit: string
  quantidade_atual: number
  estoque_id: string | null
  estoque_data: string | null
  estoque_quantidade: number | null
  quantidade_anterior: number | null
  quantidade_nova: number | null
  delta: number | null
  status: ContagemItemStatus
  contado_em: string | null
}

export interface ContagemDetalheCategoria {
  category_id: string
  categoria: string
  total_itens: number
  itens_contados: number
  itens_alterados: number
  itens_sem_alteracao: number
  itens_nao_contados: number
  items: ContagemDetalheItem[]
}

export interface ContagemDetalhe extends ContagemResumo {
  categorias: ContagemDetalheCategoria[]
}

async function parseJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) throw new Error(fallback)
  return response.json() as Promise<T>
}

export async function fetchContagemDetalhe(id: number | string) {
  return parseJson<ContagemDetalhe>(
    await fetch(`${API_URL}/api/contagens/${id}/detalhe`),
    'Falha ao carregar histórico da contagem',
  )
}

export function useContagens() {
  return useQuery({
    queryKey: ['contagens'],
    queryFn: async () =>
      parseJson<ContagemResumo[]>(
        await fetch(`${API_URL}/api/contagens`),
        'Falha ao carregar contagens',
      ),
    staleTime: 15_000,
  })
}

export function useContagemDetalhe(id: number | string) {
  return useQuery({
    queryKey: ['contagem-detalhe', id],
    queryFn: () => fetchContagemDetalhe(id),
    enabled: Boolean(id),
    staleTime: 15_000,
  })
}

export function useIniciarContagem() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async () =>
      parseJson<ContagemBase>(
        await fetch(`${API_URL}/api/contagens`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({}),
        }),
        'Falha ao iniciar contagem',
      ),
    onSuccess: (contagem) => {
      setContagemSession(contagem)
      qc.invalidateQueries({ queryKey: ['contagens'] })
    },
  })
}

export function useFinalizarContagem() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (id: number) =>
      parseJson<ContagemBase>(
        await fetch(`${API_URL}/api/contagens/${id}/finalizar`, {
          method: 'PATCH',
        }),
        'Falha ao finalizar contagem',
      ),
    onSuccess: (_, id) => {
      qc.invalidateQueries({ queryKey: ['contagens'] })
      qc.invalidateQueries({ queryKey: ['contagem-detalhe', id] })
    },
  })
}
