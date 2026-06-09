import { useEffect, useMemo, useState } from 'react'
import { createRoute } from '@tanstack/react-router'
import {
  Calculator,
  CheckCircle2,
  FileSpreadsheet,
  Mail,
  PackagePlus,
  PiggyBank,
  RefreshCcw,
  ShieldAlert,
  ShoppingCart,
  Timer,
} from 'lucide-react'
import { rootRoute } from './Root'
import { AppSelect } from '../components/AppSelect'
import { KpiCard } from '../components/KpiCard'
import { cn } from '../lib/cn'
import { downloadPurchasePlanExport, type DashboardExportFormat } from '../lib/exportData'
import { useAppearance } from '../theme/appearance'
import {
  useApprovePurchasePlan,
  useGeneratePurchasePlan,
  useLatestPurchasePlan,
  useSendPurchaseQuotes,
  useSimulatePurchasePlan,
  useUpdatePurchasePlanItem,
  type PurchasePlan,
  type PurchasePlanItem,
} from '../hooks/usePurchasePlan'

export const comprasPlanejamentoRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/compras/planejamento',
  component: ComprasPlanejamentoPage,
})

const fmt = {
  currency: (value: number) =>
    value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }),
  qty: (value: number, unit?: string | null) =>
    `${value.toLocaleString('pt-BR', { maximumFractionDigits: 2 })} ${unit ?? ''}`.trim(),
  date: (value?: string | null) =>
    value ? new Date(`${value}T00:00:00`).toLocaleDateString('pt-BR') : '-',
}

const horizonOptions = [
  { value: '7', label: '7 dias' },
  { value: '14', label: '14 dias' },
  { value: '28', label: '28 dias' },
]

const exportOptions: Array<{ value: DashboardExportFormat; label: string }> = [
  { value: 'excel', label: 'Excel' },
  { value: 'pdf', label: 'PDF' },
]

function criticalTone(label: string) {
  const normalized = label.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
  if (normalized.includes('critic') || normalized.includes('ruptura')) return 'saltim-danger-soft'
  if (normalized.includes('alerta') || normalized.includes('zerado')) return 'saltim-alert-soft'
  return 'saltim-success-soft'
}

function PlanEmptyState({
  onGenerate,
  pending,
}: {
  onGenerate: () => void
  pending: boolean
}) {
  return (
    <section className="rounded-xl border border-stone-200 bg-white p-8">
      <div className="flex max-w-3xl items-start gap-4">
        <div className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-700">
          <ShoppingCart className="size-6" strokeWidth={1.9} />
        </div>
        <div className="min-w-0">
          <h2 className="text-lg font-black text-stone-900">Plano de compra Maestro</h2>
          <p className="mt-1 text-sm font-medium leading-relaxed text-stone-500">
            Gere um plano automatico a partir do estoque atual, consumo recente, pedidos em transito,
            fornecedores e criticidade. A aprovacao final continua nas suas maos.
          </p>
          <button
            type="button"
            onClick={onGenerate}
            disabled={pending}
            className="mt-5 inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-black text-white shadow-sm transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <PackagePlus className="size-4" strokeWidth={2.2} />
            {pending ? 'Gerando...' : 'Gerar plano de compra'}
          </button>
        </div>
      </div>
    </section>
  )
}

function SupplierPanel({ item }: { item?: PurchasePlanItem }) {
  if (!item) {
    return (
      <aside className="rounded-xl border border-stone-200 bg-white p-5 text-sm font-semibold text-stone-500">
        Selecione um ingrediente para ver o ranking de fornecedores.
      </aside>
    )
  }

  return (
    <aside className="rounded-xl border border-stone-200 bg-white p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-black uppercase tracking-wide text-stone-500">Fornecedor sugerido</p>
          <h3 className="mt-1 text-base font-black text-stone-900">
            {item.selected_supplier_name ?? 'Sem fornecedor'}
          </h3>
        </div>
        <span className={cn('rounded-full border px-2.5 py-1 text-xs font-black', criticalTone(item.criticality))}>
          {item.criticality}
        </span>
      </div>
      <p className="mt-3 text-sm font-medium leading-relaxed text-stone-500">
        {item.justification ?? 'Sem justificativa registrada.'}
      </p>

      <div className="mt-5 space-y-3">
        {item.options.map(option => (
          <div
            key={option.supplier_id}
            className={cn(
              'rounded-lg border p-3',
              option.supplier_id === item.selected_supplier_id
                ? 'border-brand-300 bg-brand-50'
                : 'border-stone-200 bg-stone-50',
            )}
          >
            <div className="flex items-center justify-between gap-3">
              <p className="min-w-0 truncate text-sm font-black text-stone-900">{option.supplier_name}</p>
              <span className="text-xs font-black tabular-nums text-brand-700">
                score {option.score.toLocaleString('pt-BR', { maximumFractionDigits: 2 })}
              </span>
            </div>
            <p className="mt-1 text-xs font-semibold text-stone-500">{option.reason}</p>
            <div className="mt-2 grid grid-cols-3 gap-2 text-xs font-bold text-stone-500">
              <span>{fmt.currency(option.effective_unit_price)}</span>
              <span>{option.delivery_time_days} dias</span>
              <span>{Math.round(option.delay_risk * 100)}% risco</span>
            </div>
          </div>
        ))}
      </div>
    </aside>
  )
}

function PurchasePlanTable({
  plan,
  selectedItemId,
  setSelectedItemId,
  quantities,
  suppliers,
  setQuantities,
  setSuppliers,
  onSave,
  savingKey,
}: {
  plan: PurchasePlan
  selectedItemId?: string
  setSelectedItemId: (id: string) => void
  quantities: Record<string, string>
  suppliers: Record<string, string>
  setQuantities: (value: Record<string, string>) => void
  setSuppliers: (value: Record<string, string>) => void
  onSave: (item: PurchasePlanItem) => void
  savingKey?: string
}) {
  return (
    <section className="overflow-hidden rounded-xl border border-stone-200 bg-white">
      <div className="border-b border-stone-200 p-5">
        <h2 className="text-base font-black text-stone-900">Itens recomendados</h2>
        <p className="mt-1 text-sm font-semibold text-stone-500">
          Ajuste quantidade e fornecedor antes de cotar ou aprovar.
        </p>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-[1120px] w-full text-left text-sm">
          <thead className="bg-stone-50 text-xs font-black uppercase tracking-wide text-stone-500">
            <tr>
              <th className="px-5 py-3">Ingrediente</th>
              <th className="px-4 py-3">Estoque</th>
              <th className="px-4 py-3">Transito</th>
              <th className="px-4 py-3">Sugestao</th>
              <th className="px-4 py-3">Aprovado</th>
              <th className="px-4 py-3">Fornecedor</th>
              <th className="px-4 py-3">Total</th>
              <th className="px-4 py-3">Cobertura</th>
              <th className="px-5 py-3">Acao</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-stone-200">
            {plan.items.map(item => (
              <tr
                key={item.ingredient_id}
                onClick={() => setSelectedItemId(item.ingredient_id)}
                className={cn(
                  'cursor-pointer transition hover:bg-stone-50',
                  selectedItemId === item.ingredient_id && 'bg-brand-50/70',
                )}
              >
                <td className="px-5 py-4">
                  <div className="min-w-0">
                    <div className="font-black text-stone-900">{item.ingredient_name}</div>
                    <div className="mt-1 flex items-center gap-2">
                      <span className="text-xs font-bold text-stone-500">{item.category}</span>
                      <span className={cn('rounded-full border px-2 py-0.5 text-[11px] font-black', criticalTone(item.criticality))}>
                        {item.criticality}
                      </span>
                    </div>
                  </div>
                </td>
                <td className="px-4 py-4 font-bold tabular-nums text-stone-700">{fmt.qty(item.current_qty, item.unit)}</td>
                <td className="px-4 py-4 font-bold tabular-nums text-stone-500">{fmt.qty(item.in_transit_qty, item.unit)}</td>
                <td className="px-4 py-4 font-black tabular-nums text-brand-700">{fmt.qty(item.recommended_qty, item.unit)}</td>
                <td className="px-4 py-4">
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={quantities[item.ingredient_id] ?? String(item.approved_qty)}
                    onChange={event =>
                      setQuantities({
                        ...quantities,
                        [item.ingredient_id]: event.target.value,
                      })
                    }
                    onClick={event => event.stopPropagation()}
                    className="h-9 w-28 rounded-lg border border-stone-200 bg-stone-50 px-3 text-sm font-bold text-stone-900 outline-none transition focus:border-brand-600 focus:ring-4 focus:ring-brand-100"
                  />
                </td>
                <td className="px-4 py-4">
                  <AppSelect
                    value={suppliers[item.ingredient_id] ?? item.selected_supplier_id ?? ''}
                    options={item.options.map(option => ({
                      value: option.supplier_id,
                      label: option.supplier_name,
                    }))}
                    onChange={value =>
                      setSuppliers({
                        ...suppliers,
                        [item.ingredient_id]: value,
                      })
                    }
                    className="min-w-56"
                  />
                </td>
                <td className="px-4 py-4 font-black tabular-nums text-stone-900">{fmt.currency(item.estimated_total)}</td>
                <td className="px-4 py-4 font-bold tabular-nums text-stone-600">
                  {item.coverage_days.toLocaleString('pt-BR', { maximumFractionDigits: 1 })} dias
                </td>
                <td className="px-5 py-4">
                  <button
                    type="button"
                    onClick={event => {
                      event.stopPropagation()
                      onSave(item)
                    }}
                    disabled={savingKey === item.ingredient_id}
                    className="inline-flex items-center gap-2 rounded-lg border border-stone-200 bg-white px-3 py-2 text-xs font-black text-stone-700 transition hover:border-brand-300 hover:text-brand-700 disabled:opacity-60"
                  >
                    <CheckCircle2 className="size-4" strokeWidth={2.1} />
                    {savingKey === item.ingredient_id ? 'Salvando' : 'Salvar'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

export function ComprasPlanejamentoPage() {
  const { themeId } = useAppearance()
  const latest = useLatestPurchasePlan()
  const generate = useGeneratePurchasePlan()
  const updateItem = useUpdatePurchasePlanItem()
  const sendQuotes = useSendPurchaseQuotes()
  const approve = useApprovePurchasePlan()
  const simulate = useSimulatePurchasePlan()
  const [horizon, setHorizon] = useState('7')
  const [selectedItemId, setSelectedItemId] = useState<string>()
  const [quantities, setQuantities] = useState<Record<string, string>>({})
  const [suppliers, setSuppliers] = useState<Record<string, string>>({})
  const [savingKey, setSavingKey] = useState<string>()
  const [exportFormat, setExportFormat] = useState<DashboardExportFormat>('excel')
  const [exporting, setExporting] = useState(false)
  const [error, setError] = useState('')

  const plan = latest.data ?? null
  const selectedItem = useMemo(
    () => plan?.items.find(item => item.ingredient_id === selectedItemId) ?? plan?.items[0],
    [plan, selectedItemId],
  )

  useEffect(() => {
    if (!plan) return
    setSelectedItemId(previous => previous ?? plan.items[0]?.ingredient_id)
    setQuantities(Object.fromEntries(plan.items.map(item => [item.ingredient_id, String(item.approved_qty)])))
    setSuppliers(Object.fromEntries(plan.items.map(item => [item.ingredient_id, item.selected_supplier_id ?? ''])))
  }, [plan?.id])

  async function handleGenerate() {
    setError('')
    try {
      await generate.mutateAsync({ horizon_days: Number(horizon) })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Nao foi possivel gerar o plano.')
    }
  }

  async function handleSave(item: PurchasePlanItem) {
    if (!plan) return
    setError('')
    setSavingKey(item.ingredient_id)
    try {
      await updateItem.mutateAsync({
        planId: plan.id,
        ingredientId: item.ingredient_id,
        approved_qty: Number(quantities[item.ingredient_id] ?? item.approved_qty),
        selected_supplier_id: suppliers[item.ingredient_id] ?? item.selected_supplier_id,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Nao foi possivel salvar o item.')
    } finally {
      setSavingKey(undefined)
    }
  }

  async function handleSimulate() {
    if (!plan) return
    setError('')
    try {
      await simulate.mutateAsync({
        planId: plan.id,
        items: plan.items.map(item => ({
          ingredient_id: item.ingredient_id,
          approved_qty: Number(quantities[item.ingredient_id] ?? item.approved_qty),
          selected_supplier_id: suppliers[item.ingredient_id] ?? item.selected_supplier_id,
        })),
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Nao foi possivel simular o plano.')
    }
  }

  async function handleExport() {
    if (!plan) return
    setError('')
    setExporting(true)
    try {
      await downloadPurchasePlanExport(plan.id, exportFormat, themeId)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Nao foi possivel exportar.')
    } finally {
      setExporting(false)
    }
  }

  async function handleSendQuotes() {
    if (!plan) return
    setError('')
    try {
      await sendQuotes.mutateAsync(plan.id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Nao foi possivel enviar cotacoes.')
    }
  }

  async function handleApprove() {
    if (!plan) return
    setError('')
    try {
      await approve.mutateAsync(plan.id)
      await latest.refetch()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Nao foi possivel aprovar o plano.')
    }
  }

  const isBusy = generate.isPending || sendQuotes.isPending || approve.isPending

  if (latest.isLoading) {
    return <main className="p-8 text-sm font-semibold text-stone-500">Carregando plano de compra...</main>
  }

  return (
    <main className="min-h-screen bg-stone-50 p-6 lg:p-8">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-black uppercase tracking-wide text-brand-700">Centro de Compras Autonomo</p>
          <h1 className="mt-1 text-2xl font-black text-stone-900">Plano de compra Maestro</h1>
          <p className="mt-1 text-sm font-semibold text-stone-500">
            {plan
              ? `Plano #${plan.id} · ${fmt.date(plan.date_from)} a ${fmt.date(plan.date_to)} · ${plan.status}`
              : 'Da contagem finalizada aos pedidos em transito, sem conta de guardanapo.'}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <AppSelect value={horizon} options={horizonOptions} onChange={setHorizon} className="w-32" />
          <button
            type="button"
            onClick={handleGenerate}
            disabled={generate.isPending}
            className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-black text-white transition hover:bg-brand-700 disabled:opacity-60"
          >
            <RefreshCcw className="size-4" strokeWidth={2.1} />
            {generate.isPending ? 'Gerando...' : 'Gerar plano'}
          </button>
          {plan && (
            <>
              <AppSelect
                value={exportFormat}
                options={exportOptions}
                onChange={value => setExportFormat((value || 'excel') as DashboardExportFormat)}
                className="w-28"
              />
              <button
                type="button"
                onClick={handleExport}
                disabled={exporting}
                className="inline-flex items-center gap-2 rounded-lg border border-stone-200 bg-white px-4 py-2 text-sm font-black text-stone-800 transition hover:border-brand-300 hover:text-brand-700 disabled:opacity-60"
              >
                <FileSpreadsheet className="size-4" strokeWidth={2.1} />
                {exporting ? 'Exportando...' : 'Exportar'}
              </button>
            </>
          )}
        </div>
      </div>

      {(error || latest.isError) && (
        <div className="mb-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm font-bold text-red-700">
          {error || 'Nao foi possivel carregar o plano de compra.'}
        </div>
      )}

      {!plan ? (
        <PlanEmptyState onGenerate={handleGenerate} pending={generate.isPending} />
      ) : (
        <div className="space-y-6">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <KpiCard icon={ShoppingCart} label="Custo estimado" value={fmt.currency(plan.approved_total || plan.total_estimated)} detail={`${plan.items.length} itens no plano`} />
            <KpiCard icon={ShieldAlert} label="Itens criticos" value={String(plan.critical_items_count)} detail="Prioridade de revisao" tone="red" />
            <KpiCard icon={Timer} label="Cobertura media" value={`${plan.avg_coverage_days.toLocaleString('pt-BR', { maximumFractionDigits: 1 })} dias`} detail={`Horizonte de ${plan.horizon_days} dias`} tone="blue" />
            <KpiCard icon={PiggyBank} label="Economia potencial" value={fmt.currency(plan.savings_potential)} detail="Comparacao com menor preco viavel" tone="green" />
          </div>

          <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
            <PurchasePlanTable
              plan={plan}
              selectedItemId={selectedItem?.ingredient_id}
              setSelectedItemId={setSelectedItemId}
              quantities={quantities}
              suppliers={suppliers}
              setQuantities={setQuantities}
              setSuppliers={setSuppliers}
              onSave={handleSave}
              savingKey={savingKey}
            />
            <div className="space-y-4">
              <SupplierPanel item={selectedItem} />
              <section className="rounded-xl border border-stone-200 bg-white p-5">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-xs font-black uppercase tracking-wide text-stone-500">Simulacao</p>
                    <h2 className="mt-1 text-base font-black text-stone-900">Impacto antes de aprovar</h2>
                  </div>
                  <button
                    type="button"
                    onClick={handleSimulate}
                    disabled={simulate.isPending}
                    className="inline-flex items-center gap-2 rounded-lg border border-stone-200 bg-white px-3 py-2 text-xs font-black text-stone-700 transition hover:border-brand-300 hover:text-brand-700 disabled:opacity-60"
                  >
                    <Calculator className="size-4" strokeWidth={2.1} />
                    {simulate.isPending ? 'Simulando' : 'Simular'}
                  </button>
                </div>
                {simulate.data ? (
                  <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                    <div className="rounded-lg bg-stone-50 p-3">
                      <p className="text-xs font-black uppercase text-stone-500">Total</p>
                      <p className="mt-1 font-black text-stone-900">{fmt.currency(simulate.data.approved_total)}</p>
                    </div>
                    <div className="rounded-lg bg-stone-50 p-3">
                      <p className="text-xs font-black uppercase text-stone-500">Risco</p>
                      <p className="mt-1 font-black text-stone-900">{simulate.data.rupture_risk_items} itens</p>
                    </div>
                    <div className="rounded-lg bg-stone-50 p-3">
                      <p className="text-xs font-black uppercase text-stone-500">Cobertura</p>
                      <p className="mt-1 font-black text-stone-900">{simulate.data.projected_coverage_days} dias</p>
                    </div>
                    <div className="rounded-lg bg-stone-50 p-3">
                      <p className="text-xs font-black uppercase text-stone-500">Economia</p>
                      <p className="mt-1 font-black text-stone-900">{fmt.currency(simulate.data.savings_potential)}</p>
                    </div>
                    {simulate.data.notes.length > 0 && (
                      <div className="col-span-2 rounded-lg border border-stone-200 bg-stone-50 p-3">
                        <p className="text-xs font-black uppercase text-stone-500">Alertas</p>
                        <ul className="mt-2 space-y-1 text-xs font-semibold text-stone-600">
                          {simulate.data.notes.map(note => <li key={note}>{note}</li>)}
                        </ul>
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="mt-3 text-sm font-semibold text-stone-500">
                    Rode a simulacao depois de editar quantidades ou fornecedores.
                  </p>
                )}
              </section>
            </div>
          </div>

          <section className="rounded-xl border border-stone-200 bg-white p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-base font-black text-stone-900">Cotações e aprovação</h2>
                <p className="mt-1 text-sm font-semibold text-stone-500">
                  Emails corporativos por fornecedor e criação de pedidos em trânsito.
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={handleSendQuotes}
                  disabled={isBusy}
                  className="inline-flex items-center gap-2 rounded-lg border border-stone-200 bg-white px-4 py-2 text-sm font-black text-stone-800 transition hover:border-brand-300 hover:text-brand-700 disabled:opacity-60"
                >
                  <Mail className="size-4" strokeWidth={2.1} />
                  {sendQuotes.isPending ? 'Enviando...' : 'Enviar cotações'}
                </button>
                <button
                  type="button"
                  onClick={handleApprove}
                  disabled={isBusy}
                  className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-black text-white transition hover:bg-brand-700 disabled:opacity-60"
                >
                  <CheckCircle2 className="size-4" strokeWidth={2.1} />
                  {approve.isPending ? 'Aprovando...' : 'Aprovar pedidos'}
                </button>
              </div>
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              {plan.quotes.map(quote => (
                <div key={quote.supplier_id} className="rounded-lg border border-stone-200 bg-stone-50 p-4">
                  <p className="truncate text-sm font-black text-stone-900">{quote.supplier_name}</p>
                  <p className="mt-1 truncate text-xs font-semibold text-stone-500">{quote.email ?? 'Sem email cadastrado'}</p>
                  <div className="mt-3 flex items-center justify-between gap-3">
                    <span className="rounded-full border border-stone-200 bg-white px-2 py-1 text-xs font-black text-stone-600">{quote.status}</span>
                    <span className="text-sm font-black tabular-nums text-brand-700">{fmt.currency(quote.total_estimated)}</span>
                  </div>
                  {quote.notes && <p className="mt-2 text-xs font-semibold text-stone-500">{quote.notes}</p>}
                </div>
              ))}
            </div>
          </section>
        </div>
      )}
    </main>
  )
}
