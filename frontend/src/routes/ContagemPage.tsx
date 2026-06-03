import { createRoute, Link, useNavigate } from '@tanstack/react-router'
import { CalendarClock, CheckCircle2, ClipboardList, Play, RotateCcw } from 'lucide-react'
import { rootRoute } from './Root'
import { hydrateContagemSession, resetContagem } from '../hooks/useContagem'
import {
  fetchContagemDetalhe,
  getContagemHoje,
  useContagens,
  useIniciarContagem,
  type ContagemResumo,
} from '../hooks/useContagens'
import { cn } from '../lib/cn'

export const contagemRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/estoque/contagem',
  component: ContagemPage,
})

const fmt = {
  dateTime: (value: string | null) =>
    value
      ? new Date(value).toLocaleString('pt-BR', {
          timeZone: 'America/Recife',
          day: '2-digit',
          month: '2-digit',
          year: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
        })
      : '-',
  date: (value: string | null) =>
    value
      ? new Date(`${value}T00:00:00`).toLocaleDateString('pt-BR', {
          timeZone: 'America/Recife',
          day: '2-digit',
          month: '2-digit',
          year: 'numeric',
        })
      : '-',
  percent: (contagem: ContagemResumo) =>
    contagem.total_itens === 0
      ? 0
      : Math.round((contagem.itens_contados / contagem.total_itens) * 100),
}

export function ContagemPage() {
  const navigate = useNavigate()
  const { data: contagens = [], isFetching, isError } = useContagens()
  const iniciar = useIniciarContagem()
  const contagemHoje = getContagemHoje(contagens)

  const buttonLabel = contagemHoje
    ? contagemHoje.status === 'finalizada'
      ? 'Atualizar contagem de hoje'
      : 'Continuar contagem de hoje'
    : 'Iniciar contagem de hoje'

  async function handleIniciar() {
    resetContagem()
    const contagem = await iniciar.mutateAsync()
    const detalhe = await fetchContagemDetalhe(contagem.id)
    hydrateContagemSession(contagem, detalhe.categorias.flatMap((categoria) => categoria.items))
    navigate({ to: '/estoque/contagem/atual' })
  }

  return (
    <div className="flex h-screen flex-col bg-surface">
      <header className="flex h-[73px] flex-shrink-0 items-center justify-between gap-4 border-b border-stone-200 bg-white px-8">
        <div className="min-w-0">
          <h1 className="text-xl font-semibold text-stone-900">Histórico de contagens</h1>
          <p className="mt-0.5 text-xs text-stone-400">
            {isFetching ? 'Carregando...' : `${contagens.length} contagem${contagens.length !== 1 ? 's' : ''}`}
          </p>
        </div>
        <button
          onClick={handleIniciar}
          disabled={iniciar.isPending}
          className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {iniciar.isPending ? (
            <RotateCcw className="size-4 animate-spin" strokeWidth={2} />
          ) : (
            <Play className="size-4" strokeWidth={2} />
          )}
          {buttonLabel}
        </button>
      </header>

      <main className="flex-1 overflow-auto p-6">
        <section className="overflow-hidden rounded-xl border border-stone-200 bg-white">
          <div className="border-b border-stone-100 px-5 py-4">
            <h2 className="text-sm font-black text-stone-900">Contagens registradas</h2>
            <p className="mt-1 text-xs text-stone-400">
              Itens alterados, sem alteração e pendentes por sessão.
            </p>
          </div>

          {isError ? (
            <EmptyState message="Não foi possível carregar o histórico." />
          ) : contagens.length === 0 && !isFetching ? (
            <EmptyState message="Nenhuma contagem registrada ainda." />
          ) : (
            <div className="divide-y divide-stone-100">
              {contagens.map((contagem) => (
                <ContagemRow key={contagem.id} contagem={contagem} />
              ))}
              {isFetching && contagens.length === 0 && (
                <div className="px-5 py-12 text-center text-sm text-stone-400">Carregando...</div>
              )}
            </div>
          )}
        </section>
      </main>
    </div>
  )
}

function ContagemRow({ contagem }: { contagem: ContagemResumo }) {
  const pct = fmt.percent(contagem)
  const finalizada = contagem.status === 'finalizada'

  return (
    <Link
      to="/estoque/contagem/historico/$id"
      params={{ id: String(contagem.id) }}
      className="grid grid-cols-[minmax(0,1.3fr)_170px_220px_160px] items-center gap-5 px-5 py-4 transition-colors hover:bg-stone-50"
    >
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <span className="truncate text-sm font-bold text-stone-900">{contagem.label}</span>
          <span
            className={cn(
              'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-bold',
              finalizada ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700',
            )}
          >
            {finalizada ? <CheckCircle2 className="size-3" /> : <CalendarClock className="size-3" />}
            {finalizada ? 'Finalizada' : 'Em andamento'}
          </span>
        </div>
        <p className="mt-1 text-xs text-stone-400">
          Contagem de {fmt.date(contagem.data_contagem)} · criada em {fmt.dateTime(contagem.criada_em)}
        </p>
      </div>

      <div>
        <p className="text-[11px] font-bold uppercase tracking-wide text-stone-400">Progresso</p>
        <p className="mt-1 text-sm font-black tabular-nums text-stone-900">
          {contagem.itens_contados} / {contagem.total_itens}
          <span className="ml-1 text-xs text-stone-400">itens</span>
        </p>
        <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-stone-100">
          <div
            className="h-full rounded-full bg-brand-600 transition-all"
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2">
        <Metric label="Alterados" value={contagem.itens_alterados} tone="orange" />
        <Metric label="Sem alteração" value={contagem.itens_sem_alteracao} tone="green" />
        <Metric label="Pendentes" value={contagem.itens_nao_contados} tone="stone" />
      </div>

      <div className="text-right">
        <p className="text-[11px] font-bold uppercase tracking-wide text-stone-400">Finalizada</p>
        <p className="mt-1 text-xs font-semibold tabular-nums text-stone-600">
          {fmt.dateTime(contagem.finalizada_em)}
        </p>
      </div>
    </Link>
  )
}

function Metric({
  label,
  value,
  tone,
}: {
  label: string
  value: number
  tone: 'orange' | 'green' | 'stone'
}) {
  const classes = {
    orange: 'bg-orange-50 text-orange-700',
    green: 'bg-green-50 text-green-700',
    stone: 'bg-stone-100 text-stone-600',
  }

  return (
    <div className={cn('rounded-lg px-3 py-2 text-center', classes[tone])}>
      <p className="text-sm font-black tabular-nums">{value}</p>
      <p className="mt-0.5 truncate text-[10px] font-bold uppercase tracking-wide">{label}</p>
    </div>
  )
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center px-5 py-16 text-center">
      <ClipboardList className="size-10 text-stone-300" strokeWidth={1.8} />
      <p className="mt-3 text-sm font-medium text-stone-500">{message}</p>
    </div>
  )
}
