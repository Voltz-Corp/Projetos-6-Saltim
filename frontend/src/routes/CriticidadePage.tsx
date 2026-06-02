import { createRoute } from '@tanstack/react-router'
import type { ReactNode } from 'react'
import { Activity, AlertTriangle, CheckCircle2, DatabaseZap, Gauge, XCircle } from 'lucide-react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { rootRoute } from './Root'
import {
  useCriticidadeReport,
  type CriticidadeItem,
  type CriticidadeRun,
} from '../hooks/useCriticidadeReport'
import { KpiCard } from '../components/KpiCard'
import { cn } from '../lib/cn'

export const criticidadeRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/ml/criticidade',
  component: CriticidadePage,
})

const COLORS = {
  ok: '#2D7A3A',
  alert: '#E4332B',
  blue: '#52B9EB',
  orange: '#F07820',
  stone: '#78716c',
}

const fmt = {
  number: (value: number, digits = 0) =>
    value.toLocaleString('pt-BR', {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    }),
  percent: (value: number) =>
    `${(value * 100).toLocaleString('pt-BR', {
      minimumFractionDigits: 1,
      maximumFractionDigits: 1,
    })}%`,
  date: (value: string | null) =>
    value
      ? new Date(`${value}T00:00:00`).toLocaleDateString('pt-BR', {
          day: '2-digit',
          month: '2-digit',
          year: 'numeric',
        })
      : '-',
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
}

function tooltipNumber(value: unknown) {
  return fmt.number(Number(value) || 0)
}

function runStatus(run: CriticidadeRun) {
  if (run.status === 'success') {
    return {
      label: 'Relatório gerado',
      tone: 'green' as const,
      icon: CheckCircle2,
    }
  }
  if (run.status === 'pending_contagem') {
    return {
      label: 'Contagem pendente',
      tone: 'orange' as const,
      icon: AlertTriangle,
    }
  }
  if (run.status === 'failed') {
    return {
      label: 'Falha no job',
      tone: 'red' as const,
      icon: XCircle,
    }
  }
  return {
    label: 'Sem relatório',
    tone: 'blue' as const,
    icon: DatabaseZap,
  }
}

function asNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function mlflowMetric(run: CriticidadeRun, key: string): number | null {
  const mlflow = run.metrics?.['mlflow']
  if (!mlflow || typeof mlflow !== 'object') return null
  return asNumber((mlflow as Record<string, unknown>)[key])
}

function Panel({
  title,
  subtitle,
  children,
}: {
  title: string
  subtitle?: string
  children: ReactNode
}) {
  return (
    <section className="min-w-0 overflow-hidden rounded-xl border border-stone-200 bg-white">
      <div className="border-b border-stone-100 px-5 py-4">
        <h2 className="text-sm font-semibold text-stone-900">{title}</h2>
        {subtitle && <p className="mt-1 text-xs font-medium text-stone-400">{subtitle}</p>}
      </div>
      <div className="p-4">{children}</div>
    </section>
  )
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex h-56 items-center justify-center text-center text-sm font-medium text-stone-400">
      {message}
    </div>
  )
}

export function CriticidadePage() {
  const { data, isFetching, isError } = useCriticidadeReport()
  const report = data
  const run = report?.run
  const status = run ? runStatus(run) : null
  const isSuccess = run?.status === 'success'
  const StatusIcon = status?.icon ?? Activity

  const distribution = report?.distribution ?? []
  const categoryData = (report?.categories ?? []).slice(0, 10).map((category) => ({
    category:
      category.category.length > 22
        ? `${category.category.slice(0, 21)}...`
        : category.category,
    alertas: category.alert_count,
    ok: category.ok_count,
  }))
  const criticalItems = report?.critical_items.slice(0, 12) ?? []

  const rmse = run ? mlflowMetric(run, 'rmse') : null
  const mae = run ? mlflowMetric(run, 'mae') : null
  const r2 = run ? mlflowMetric(run, 'r2') : null
  const f1 = run ? mlflowMetric(run, 'f1_macro') : null

  return (
    <div className="flex h-screen flex-col bg-surface">
      <header className="flex flex-shrink-0 items-center justify-between gap-4 border-b border-stone-200 bg-white px-8 py-4">
        <div className="min-w-0">
          <h1 className="text-xl font-semibold text-stone-900">Relatório de criticidade</h1>
          <p className="mt-0.5 text-xs text-stone-400">
            {isFetching
              ? 'Carregando...'
              : `XGBoost · contagem de ${fmt.date(run?.reference_date ?? null)}`}
          </p>
        </div>
        <div
          className={cn(
            'inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-bold',
            status?.tone === 'green' && 'bg-green-50 text-green-700',
            status?.tone === 'orange' && 'bg-orange-50 text-orange-700',
            status?.tone === 'red' && 'bg-red-50 text-red-700',
            status?.tone === 'blue' && 'bg-blue-50 text-blue-700',
          )}
        >
          <StatusIcon className="size-4" strokeWidth={2} />
          {status?.label ?? 'Carregando'}
        </div>
      </header>

      <main className="flex-1 overflow-auto p-6">
        {isError ? (
          <EmptyState message="Não foi possível carregar o relatório de criticidade." />
        ) : (
          <div className="space-y-5">
            {run && !isSuccess && (
              <div className="rounded-xl border border-amber-200 bg-amber-50 px-5 py-4 text-sm font-medium text-amber-800">
                {run.error_message || 'O relatório ainda não está disponível para a contagem de hoje.'}
              </div>
            )}

            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <KpiCard
                icon={StatusIcon}
                label="Status"
                value={status?.label ?? '-'}
                detail={`Executado em ${fmt.dateTime(run?.generated_at ?? null)}`}
                tone={status?.tone ?? 'blue'}
                showComparisonBadge={false}
              />
              <KpiCard
                icon={AlertTriangle}
                label="Alerta"
                value={fmt.number(run?.alert_count ?? 0)}
                detail={`${fmt.percent(run?.alert_rate ?? 0)} dos itens avaliados`}
                tone="red"
                showComparisonBadge={false}
              />
              <KpiCard
                icon={CheckCircle2}
                label="OK"
                value={fmt.number(run?.ok_count ?? 0)}
                detail={`${fmt.number(run?.total_items ?? 0)} itens no relatório`}
                tone="green"
                showComparisonBadge={false}
              />
              <KpiCard
                icon={Gauge}
                label="Estabilidade"
                value={String(run?.stability?.['status'] ?? '-').replace(/_/g, ' ')}
                detail={run?.model_uri ?? 'Modelo XGBoost final'}
                tone="blue"
                showComparisonBadge={false}
              />
            </div>

            <div className="grid gap-5 xl:grid-cols-[0.85fr_1.15fr]">
              <Panel title="Distribuição" subtitle="Itens por criticidade prevista">
                {distribution.length === 0 ? (
                  <EmptyState message="Sem distribuição calculada." />
                ) : (
                  <div className="h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={distribution}
                          dataKey="count"
                          nameKey="status"
                          innerRadius={70}
                          outerRadius={105}
                          paddingAngle={3}
                        >
                          {distribution.map((entry) => (
                            <Cell
                              key={entry.status}
                              fill={entry.status === 'OK' ? COLORS.ok : COLORS.alert}
                            />
                          ))}
                        </Pie>
                        <Tooltip formatter={tooltipNumber} />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </Panel>

              <Panel title="Categorias" subtitle="Top categorias por volume de alerta">
                {categoryData.length === 0 ? (
                  <EmptyState message="Sem categorias calculadas." />
                ) : (
                  <div className="h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={categoryData} layout="vertical" margin={{ left: 12, right: 18 }}>
                        <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e7e5e4" />
                        <XAxis type="number" tick={{ fontSize: 11, fill: '#78716c' }} />
                        <YAxis
                          dataKey="category"
                          type="category"
                          width={132}
                          tick={{ fontSize: 11, fill: '#78716c' }}
                        />
                        <Tooltip formatter={tooltipNumber} />
                        <Bar dataKey="alertas" stackId="a" fill={COLORS.alert} radius={[0, 4, 4, 0]} />
                        <Bar dataKey="ok" stackId="a" fill={COLORS.ok} radius={[0, 4, 4, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </Panel>
            </div>

            <div className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
              <Panel title="Itens críticos" subtitle="Ranking operacional do último relatório">
                {criticalItems.length === 0 ? (
                  <EmptyState message="Nenhum item crítico no relatório atual." />
                ) : (
                  <ItemsTable items={criticalItems} compact={false} />
                )}
              </Panel>

              <Panel title="Métricas do XGBoost" subtitle="Rodada final registrada no MLflow">
                <div className="grid grid-cols-2 gap-3">
                  <MetricTile label="RMSE" value={rmse} />
                  <MetricTile label="MAE" value={mae} />
                  <MetricTile label="R²" value={r2} />
                  <MetricTile label="F1 macro" value={f1} />
                </div>
              </Panel>
            </div>

            <div className="grid gap-5 xl:grid-cols-2">
              <Panel title="Exemplos críticos" subtitle="Linhas escolhidas como alerta">
                {(report?.examples_critical ?? []).length === 0 ? (
                  <EmptyState message="Sem exemplos críticos no relatório atual." />
                ) : (
                  <ItemsTable items={report?.examples_critical ?? []} compact />
                )}
              </Panel>

              <Panel title="Exemplos não críticos" subtitle="Linhas escolhidas como OK">
                {(report?.examples_ok ?? []).length === 0 ? (
                  <EmptyState message="Sem exemplos OK no relatório atual." />
                ) : (
                  <ItemsTable items={report?.examples_ok ?? []} compact />
                )}
              </Panel>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

function MetricTile({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="rounded-lg border border-stone-200 bg-stone-50 px-4 py-3">
      <p className="text-[11px] font-bold uppercase tracking-wide text-stone-400">{label}</p>
      <p className="mt-1 text-xl font-black tabular-nums text-stone-900">
        {value === null ? '-' : fmt.number(value, value < 1 ? 3 : 2)}
      </p>
    </div>
  )
}

function ItemsTable({ items, compact }: { items: CriticidadeItem[]; compact: boolean }) {
  return (
    <div className="overflow-auto">
      <table className="min-w-full text-left text-sm">
        <thead>
          <tr className="border-b border-stone-100 text-[11px] font-bold uppercase tracking-wide text-stone-400">
            <th className="px-3 py-2">#</th>
            <th className="px-3 py-2">Insumo</th>
            {!compact && <th className="px-3 py-2">Categoria</th>}
            <th className="px-3 py-2 text-right">Estoque</th>
            <th className="px-3 py-2 text-right">Cobertura</th>
            <th className="px-3 py-2 text-right">Limiar</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={`${item.rank_position}-${item.ingredient_id}`} className="border-b border-stone-100 last:border-0">
              <td className="px-3 py-3 font-bold tabular-nums text-stone-500">{item.rank_position}</td>
              <td className="px-3 py-3">
                <div className="font-semibold text-stone-900">{item.ingredient_name}</div>
                <div className="mt-0.5 text-xs text-stone-400">{item.criticidade_predita}</div>
              </td>
              {!compact && <td className="px-3 py-3 text-stone-500">{item.category}</td>}
              <td className="px-3 py-3 text-right tabular-nums text-stone-700">
                {fmt.number(item.estoque_atual, 2)} {item.unit}
              </td>
              <td className="px-3 py-3 text-right tabular-nums text-stone-700">
                {fmt.percent(item.cobertura_estoque_pct)}
              </td>
              <td className="px-3 py-3 text-right tabular-nums text-stone-700">
                {fmt.percent(item.limiar_critico_predito_pct)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
