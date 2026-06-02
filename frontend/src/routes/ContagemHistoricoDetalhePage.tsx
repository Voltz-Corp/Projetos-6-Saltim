import { useState } from 'react'
import { createRoute, useNavigate } from '@tanstack/react-router'
import { ArrowLeft, ArrowUpDown, CheckCircle2, ChevronDown, CircleDashed, Play } from 'lucide-react'
import { rootRoute } from './Root'
import { useContagemDetalhe, type ContagemDetalheItem, type ContagemItemStatus } from '../hooks/useContagens'
import { hydrateContagemSession } from '../hooks/useContagem'
import { cn } from '../lib/cn'

export const contagemHistoricoDetalheRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/estoque/contagem/historico/$id',
  component: ContagemHistoricoDetalhePage,
})

const fmt = {
  dateTime: (value: string | null) =>
    value
      ? new Date(value).toLocaleString('pt-BR', {
          day: '2-digit',
          month: '2-digit',
          year: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
        })
      : '-',
  qty: (value: number | null, unit: string) =>
    value === null
      ? '-'
      : `${value.toLocaleString('pt-BR', { maximumFractionDigits: 3 })} ${unit}`,
  delta: (value: number | null, unit: string) => {
    if (value === null) return '-'
    const sign = value > 0 ? '+' : ''
    return `${sign}${value.toLocaleString('pt-BR', { maximumFractionDigits: 3 })} ${unit}`
  },
}

export function ContagemHistoricoDetalhePage() {
  const navigate = useNavigate()
  const { id } = contagemHistoricoDetalheRoute.useParams()
  const { data, isFetching, isError } = useContagemDetalhe(id)
  const [openCategories, setOpenCategories] = useState<Set<string>>(() => new Set())

  function toggleCategory(categoryId: string) {
    setOpenCategories((current) => {
      const next = new Set(current)
      if (next.has(categoryId)) next.delete(categoryId)
      else next.add(categoryId)
      return next
    })
  }

  if (isFetching && !data) {
    return <div className="p-8 text-sm text-stone-400">Carregando...</div>
  }

  if (isError || !data) {
    return <div className="p-8 text-sm text-stone-400">Contagem não encontrada.</div>
  }

  function handleContinuar() {
    if (!data) return
    hydrateContagemSession(
      data,
      data.categorias.flatMap((categoria) => categoria.items),
    )
    navigate({ to: '/estoque/contagem/atual' })
  }

  return (
    <div className="flex h-screen flex-col bg-surface">
      <header className="flex flex-shrink-0 items-center gap-3 border-b border-stone-200 bg-white px-8 py-4">
        <button
          type="button"
          onClick={() => navigate({ to: '/estoque/contagem' })}
          className="flex size-9 items-center justify-center rounded-lg border border-stone-200 text-stone-500 transition hover:bg-stone-50 hover:text-stone-900"
          aria-label="Voltar"
        >
          <ArrowLeft className="size-4" strokeWidth={2} />
        </button>
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-xl font-semibold text-stone-900">{data.label}</h1>
          <p className="mt-0.5 text-xs text-stone-400">
            {data.status === 'finalizada' ? 'Finalizada' : 'Em andamento'} · criada em {fmt.dateTime(data.criada_em)}
          </p>
        </div>
        <SummaryPill label="Contados" value={`${data.itens_contados}/${data.total_itens}`} tone="brand" />
        <SummaryPill label="Alterados" value={data.itens_alterados} tone="orange" />
        <SummaryPill label="Sem alteração" value={data.itens_sem_alteracao} tone="green" />
        <SummaryPill label="Pendentes" value={data.itens_nao_contados} tone="stone" />
        {data.status === 'em_andamento' && (
          <button
            type="button"
            onClick={handleContinuar}
            className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-brand-700"
          >
            <Play className="size-4" strokeWidth={2} />
            Continuar contagem
          </button>
        )}
      </header>

      <main className="flex-1 overflow-auto p-6">
        <div className="space-y-4">
          {data.categorias.map((categoria) => (
            <CategoriaSection
              key={categoria.category_id}
              categoria={categoria}
              open={openCategories.has(categoria.category_id)}
              onToggle={() => toggleCategory(categoria.category_id)}
            />
          ))}
        </div>
      </main>
    </div>
  )
}

function CategoriaSection({
  categoria,
  open,
  onToggle,
}: {
  categoria: {
    category_id: string
    categoria: string
    total_itens: number
    itens_contados: number
    itens_alterados: number
    itens_sem_alteracao: number
    itens_nao_contados: number
    items: ContagemDetalheItem[]
  }
  open: boolean
  onToggle: () => void
}) {
  return (
    <section className="overflow-hidden rounded-xl border border-stone-200 bg-white">
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left transition-colors hover:bg-stone-50"
      >
        <div className="flex min-w-0 items-center gap-3">
          <ChevronDown
            className={cn('size-4 flex-shrink-0 text-stone-400 transition-transform', open ? 'rotate-0' : '-rotate-90')}
            strokeWidth={2}
          />
          <div className="min-w-0">
            <h2 className="truncate text-sm font-black text-stone-900">{categoria.categoria}</h2>
            <p className="mt-1 text-xs tabular-nums text-stone-400">
              {categoria.itens_contados} / {categoria.total_itens} itens contados
            </p>
          </div>
        </div>
        <div className="flex flex-shrink-0 items-center gap-2">
          <SmallMetric label="Alt." value={categoria.itens_alterados} tone="orange" />
          <SmallMetric label="Sem alt." value={categoria.itens_sem_alteracao} tone="green" />
          <SmallMetric label="Pend." value={categoria.itens_nao_contados} tone="stone" />
        </div>
      </button>
      {open && (
        <div className="overflow-auto border-t border-stone-100">
          <table className="w-full min-w-[900px] text-sm">
            <thead className="bg-stone-50 text-xs font-bold uppercase tracking-wide text-stone-400">
              <tr>
                <th className="px-5 py-3 text-left">Insumo</th>
                <th className="px-4 py-3 text-center">Status</th>
                <th className="px-4 py-3 text-right">Anterior</th>
                <th className="px-4 py-3 text-right">Contado</th>
                <th className="px-4 py-3 text-right">Delta</th>
                <th className="px-5 py-3 text-right">Registro</th>
              </tr>
            </thead>
            <tbody>
              {categoria.items.map((item) => (
                <ItemRow key={item.ingrediente_id} item={item} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

function ItemRow({ item }: { item: ContagemDetalheItem }) {
  return (
    <tr className="border-b border-stone-100 last:border-0 hover:bg-stone-50/70">
      <td className="px-5 py-3">
        <p className="font-semibold text-stone-900">{item.ingrediente_nome}</p>
        <p className="mt-0.5 text-xs text-stone-400">Estoque atual: {fmt.qty(item.quantidade_atual, item.unit)}</p>
      </td>
      <td className="px-4 py-3 text-center">
        <StatusBadge status={item.status} />
      </td>
      <td className="px-4 py-3 text-right tabular-nums text-stone-600">
        {fmt.qty(item.quantidade_anterior, item.unit)}
      </td>
      <td className="px-4 py-3 text-right tabular-nums font-semibold text-stone-900">
        {fmt.qty(item.quantidade_nova, item.unit)}
      </td>
      <td
        className={cn(
          'px-4 py-3 text-right tabular-nums font-bold',
          item.status === 'alterado' && (item.delta ?? 0) > 0 && 'text-green-700',
          item.status === 'alterado' && (item.delta ?? 0) < 0 && 'text-red-700',
          item.status !== 'alterado' && 'text-stone-400',
        )}
      >
        {fmt.delta(item.delta, item.unit)}
      </td>
      <td className="px-5 py-3 text-right text-xs tabular-nums text-stone-400">
        {fmt.dateTime(item.contado_em)}
      </td>
    </tr>
  )
}

function StatusBadge({ status }: { status: ContagemItemStatus }) {
  const config = {
    alterado: {
      label: 'Alterado',
      icon: ArrowUpDown,
      className: 'bg-orange-50 text-orange-700',
    },
    sem_alteracao: {
      label: 'Sem alteração',
      icon: CheckCircle2,
      className: 'bg-green-50 text-green-700',
    },
    nao_contado: {
      label: 'Não contado',
      icon: CircleDashed,
      className: 'bg-stone-100 text-stone-600',
    },
  }[status]
  const Icon = config.icon

  return (
    <span className={cn('inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-bold', config.className)}>
      <Icon className="size-3" strokeWidth={2} />
      {config.label}
    </span>
  )
}

function SummaryPill({
  label,
  value,
  tone,
}: {
  label: string
  value: string | number
  tone: 'brand' | 'orange' | 'green' | 'stone'
}) {
  const classes = {
    brand: 'bg-brand-50 text-brand-700',
    orange: 'bg-orange-50 text-orange-700',
    green: 'bg-green-50 text-green-700',
    stone: 'bg-stone-100 text-stone-600',
  }

  return (
    <div className={cn('min-w-24 rounded-lg px-3 py-2 text-center', classes[tone])}>
      <p className="text-sm font-black tabular-nums">{value}</p>
      <p className="mt-0.5 text-[10px] font-bold uppercase tracking-wide">{label}</p>
    </div>
  )
}

function SmallMetric({
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
    <div className={cn('rounded-lg px-2.5 py-1.5 text-center', classes[tone])}>
      <p className="text-xs font-black tabular-nums">{value}</p>
      <p className="text-[9px] font-bold uppercase tracking-wide">{label}</p>
    </div>
  )
}
