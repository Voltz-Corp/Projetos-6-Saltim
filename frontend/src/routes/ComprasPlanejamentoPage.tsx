import { useEffect, useMemo, useState } from 'react'
import { createRoute } from '@tanstack/react-router'
import {
  CheckCircle2,
  FileSpreadsheet,
  Mail,
  PackagePlus,
  PiggyBank,
  RefreshCcw,
  ShieldAlert,
  ShoppingCart,
  Timer,
  Trash2,
} from 'lucide-react'
import { rootRoute } from './Root'
import { AppSelect } from '../components/AppSelect'
import { DataTable, type DataTableHeader } from '../components/DataTable'
import { KpiCard } from '../components/KpiCard'
import { cn } from '../lib/cn'
import { downloadPurchasePlanExport, type DashboardExportFormat } from '../lib/exportData'
import { useAppearance } from '../theme/appearance'
import {
  useApprovePurchasePlan,
  useDeletePurchasePlanItem,
  useGeneratePurchasePlan,
  useLatestPurchasePlan,
  useSendPurchaseQuotes,
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
  { value: '15', label: '15 dias' },
  { value: '30', label: '30 dias' },
]

const exportOptions: Array<{ value: DashboardExportFormat; label: string }> = [
  { value: 'excel', label: 'Excel' },
  { value: 'pdf', label: 'PDF' },
]

const PURCHASE_PAGE_SIZE_OPTIONS = [10, 25, 50]
type PlanView = 'items' | 'quotes'

function criticalTone(label: string) {
  const normalized = label.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
  if (normalized.includes('emergencial') || normalized.includes('critic') || normalized.includes('ruptura')) return 'saltim-danger-soft'
  if (normalized.includes('atencao') || normalized.includes('alerta') || normalized.includes('zerado')) return 'saltim-alert-soft'
  return 'saltim-success-soft'
}

function criticalitySourceLabel(source: string) {
  if (source === 'model_report') return 'Modelo'
  if (source === 'abt_reposicao') return 'Base ML'
  return 'Regra operacional'
}

function PlanEmptyState({
  onGenerate,
  pending,
  horizonDays,
}: {
  onGenerate: () => void
  pending: boolean
  horizonDays: number
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
            Gere uma sugestao simples usando o consumo dos ultimos {horizonDays} dias
            para estimar a necessidade dos proximos {horizonDays} dias. A aprovacao final
            continua nas suas maos.
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
    <aside className="self-start rounded-xl border border-stone-200 bg-white p-5">
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

const purchasePlanHeaders: DataTableHeader[] = [
  { key: 'ingredient', content: 'Ingrediente' },
  { key: 'stock', content: 'Estoque' },
  { key: 'transit', content: 'Transito' },
  { key: 'recommended', content: 'Sugestao recente' },
  { key: 'approved', content: 'Aprovado' },
  { key: 'supplier', content: 'Fornecedor' },
  { key: 'total', content: 'Total' },
  { key: 'coverage', content: 'Cobertura' },
  { key: 'action', content: 'Acao' },
]

function PurchasePlanTable({
  plan,
  items,
  selectedItemId,
  setSelectedItemId,
  quantities,
  suppliers,
  setQuantities,
  setSuppliers,
  onQuantityBlur,
  onSupplierChange,
  onDelete,
  savingKey,
  deletingKey,
  page,
  pageSize,
  totalPages,
  onPageChange,
  onPageSizeChange,
}: {
  plan: PurchasePlan
  items: PurchasePlanItem[]
  selectedItemId?: string
  setSelectedItemId: (id: string) => void
  quantities: Record<string, string>
  suppliers: Record<string, string>
  setQuantities: (value: Record<string, string>) => void
  setSuppliers: (value: Record<string, string>) => void
  onQuantityBlur: (item: PurchasePlanItem) => void
  onSupplierChange: (item: PurchasePlanItem, supplierId: string) => void
  onDelete: (item: PurchasePlanItem) => void
  savingKey?: string
  deletingKey?: string
  page: number
  pageSize: number
  totalPages: number
  onPageChange: (page: number) => void
  onPageSizeChange: (pageSize: number) => void
}) {
  const readOnly = plan.status === 'aprovado'

  return (
    <section className="overflow-hidden rounded-xl border border-stone-200 bg-white">
      <div className="border-b border-stone-200 p-5">
        <h2 className="text-base font-black text-stone-900">Itens recomendados</h2>
        <p className="mt-1 text-sm font-semibold text-stone-500">
          Ajustes de quantidade e fornecedor sao salvos automaticamente. A criticidade prioriza
          o modelo, depois a base ML e, por ultimo, a regra operacional.
        </p>
      </div>
      <DataTable
        headers={purchasePlanHeaders}
        colSpan={purchasePlanHeaders.length}
        minWidth="1120px"
        embedded
        isEmpty={items.length === 0}
        emptyMessage="Nenhum ingrediente neste plano."
        pagination={{
          page,
          pageSize,
          total: plan.items.length,
          totalPages,
          pageSizeOptions: PURCHASE_PAGE_SIZE_OPTIONS,
          onPageChange,
          onPageSizeChange,
        }}
      >
        {items.map(item => {
          const itemBusy = savingKey === item.ingredient_id || deletingKey === item.ingredient_id
          return (
            <tr
              key={item.ingredient_id}
              onClick={() => setSelectedItemId(item.ingredient_id)}
              className={cn(
                'cursor-pointer border-b border-stone-200 transition hover:bg-stone-50',
                selectedItemId === item.ingredient_id && 'bg-brand-50/70',
              )}
            >
              <td className="px-4 py-4">
                <div className="min-w-0">
                  <div className="font-black text-stone-900">{item.ingredient_name}</div>
                  <div className="mt-1 flex flex-wrap items-center gap-2">
                    <span className="text-xs font-bold text-stone-500">{item.category}</span>
                    <span className={cn('rounded-full border px-2 py-0.5 text-[11px] font-black', criticalTone(item.criticality))}>
                      {item.criticality}
                    </span>
                    <span className="text-[10px] font-black uppercase tracking-wide text-stone-400">
                      {criticalitySourceLabel(item.criticality_source)}
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
                  onBlur={() => onQuantityBlur(item)}
                  onClick={event => event.stopPropagation()}
                  disabled={readOnly || itemBusy}
                  className="h-9 w-28 rounded-lg border border-stone-200 bg-stone-50 px-3 text-sm font-bold text-stone-900 outline-none transition focus:border-brand-600 focus:ring-4 focus:ring-brand-100 disabled:cursor-not-allowed disabled:opacity-60"
                />
              </td>
              <td className="px-4 py-4" onClick={event => event.stopPropagation()}>
                <AppSelect
                  value={suppliers[item.ingredient_id] ?? item.selected_supplier_id ?? ''}
                  options={item.options.map(option => ({
                    value: option.supplier_id,
                    label: option.supplier_name,
                  }))}
                  onChange={value => {
                    setSuppliers({ ...suppliers, [item.ingredient_id]: value })
                    onSupplierChange(item, value)
                  }}
                  isDisabled={readOnly || itemBusy}
                  className="min-w-56"
                />
              </td>
              <td className="px-4 py-4 font-black tabular-nums text-stone-900">{fmt.currency(item.estimated_total)}</td>
              <td className="px-4 py-4 font-bold tabular-nums text-stone-600">
                {item.coverage_days.toLocaleString('pt-BR', { maximumFractionDigits: 1 })} dias
              </td>
              <td className="px-4 py-4">
                <div className="flex items-center gap-2">
                  {savingKey === item.ingredient_id && (
                    <span className="text-xs font-bold text-brand-700">Salvando...</span>
                  )}
                  <button
                    type="button"
                    onClick={event => {
                      event.stopPropagation()
                      onDelete(item)
                    }}
                    disabled={readOnly || itemBusy}
                    title={readOnly ? 'Planos aprovados nao podem ser alterados' : 'Remover ingrediente'}
                    aria-label={`Remover ${item.ingredient_name}`}
                    className="flex size-9 items-center justify-center rounded-lg border border-stone-200 bg-white text-stone-400 transition hover:border-red-200 hover:bg-red-50 hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <Trash2 className="size-4" strokeWidth={2.1} />
                  </button>
                </div>
              </td>
            </tr>
          )
        })}
      </DataTable>
    </section>
  )
}

export function ComprasPlanejamentoPage() {
  const { themeId } = useAppearance()
  const latest = useLatestPurchasePlan()
  const generate = useGeneratePurchasePlan()
  const updateItem = useUpdatePurchasePlanItem()
  const deleteItem = useDeletePurchasePlanItem()
  const sendQuotes = useSendPurchaseQuotes()
  const approve = useApprovePurchasePlan()
  const [horizon, setHorizon] = useState('7')
  const [view, setView] = useState<PlanView>('items')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)
  const [selectedItemId, setSelectedItemId] = useState<string>()
  const [quantities, setQuantities] = useState<Record<string, string>>({})
  const [suppliers, setSuppliers] = useState<Record<string, string>>({})
  const [savingKey, setSavingKey] = useState<string>()
  const [deletingKey, setDeletingKey] = useState<string>()
  const [exportFormat, setExportFormat] = useState<DashboardExportFormat>('excel')
  const [exporting, setExporting] = useState(false)
  const [error, setError] = useState('')

  const plan = latest.data ?? null
  const totalPages = Math.max(1, Math.ceil((plan?.items.length ?? 0) / pageSize))
  const currentPage = Math.min(page, totalPages)
  const visibleItems = useMemo(() => {
    const start = (currentPage - 1) * pageSize
    return plan?.items.slice(start, start + pageSize) ?? []
  }, [currentPage, pageSize, plan])
  const selectedItem = useMemo(
    () => visibleItems.find(item => item.ingredient_id === selectedItemId) ?? visibleItems[0],
    [selectedItemId, visibleItems],
  )

  useEffect(() => {
    if (!plan) return
    setPage(previous => Math.min(previous, Math.max(1, Math.ceil(plan.items.length / pageSize))))
    setQuantities(Object.fromEntries(plan.items.map(item => [item.ingredient_id, String(item.approved_qty)])))
    setSuppliers(Object.fromEntries(plan.items.map(item => [item.ingredient_id, item.selected_supplier_id ?? ''])))
  }, [pageSize, plan?.id, plan?.updated_at])

  useEffect(() => {
    if (!visibleItems.length) {
      setSelectedItemId(undefined)
      return
    }
    if (!visibleItems.some(item => item.ingredient_id === selectedItemId)) {
      setSelectedItemId(visibleItems[0].ingredient_id)
    }
  }, [selectedItemId, visibleItems])

  async function handleGenerate() {
    setError('')
    try {
      await generate.mutateAsync({ horizon_days: Number(horizon) })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Nao foi possivel gerar o plano.')
    }
  }

  async function updatePlanItem(
    item: PurchasePlanItem,
    payload: { approved_qty?: number; selected_supplier_id?: string | null },
  ) {
    if (!plan || plan.status === 'aprovado') return false
    setError('')
    setSavingKey(item.ingredient_id)
    try {
      await updateItem.mutateAsync({
        planId: plan.id,
        ingredientId: item.ingredient_id,
        ...payload,
      })
      return true
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Nao foi possivel salvar o item.')
      return false
    } finally {
      setSavingKey(undefined)
    }
  }

  async function handleQuantityBlur(item: PurchasePlanItem) {
    const value = Number(quantities[item.ingredient_id])
    if (!Number.isFinite(value) || value < 0) {
      setQuantities(current => ({ ...current, [item.ingredient_id]: String(item.approved_qty) }))
      return
    }
    if (value === item.approved_qty) return
    const updated = await updatePlanItem(item, { approved_qty: value })
    if (!updated) {
      setQuantities(current => ({ ...current, [item.ingredient_id]: String(item.approved_qty) }))
    }
  }

  async function handleSupplierChange(item: PurchasePlanItem, supplierId: string) {
    if (!supplierId || supplierId === item.selected_supplier_id) return
    const updated = await updatePlanItem(item, { selected_supplier_id: supplierId })
    if (!updated) {
      setSuppliers(current => ({ ...current, [item.ingredient_id]: item.selected_supplier_id ?? '' }))
    }
  }

  async function handleDelete(item: PurchasePlanItem) {
    if (!plan || plan.status === 'aprovado') return
    if (!window.confirm(`Remover ${item.ingredient_name} do plano de compra?`)) return
    setError('')
    setDeletingKey(item.ingredient_id)
    try {
      await deleteItem.mutateAsync({ planId: plan.id, ingredientId: item.ingredient_id })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Nao foi possivel remover o item.')
    } finally {
      setDeletingKey(undefined)
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

  const hasPendingItemChange = updateItem.isPending || deleteItem.isPending
  const isBusy = generate.isPending || sendQuotes.isPending || approve.isPending || hasPendingItemChange
  const horizonDays = Number(horizon)

  if (latest.isLoading) {
    return <main className="p-8 text-sm font-semibold text-stone-500">Carregando plano de compra...</main>
  }

  return (
    <main className="h-screen overflow-y-auto bg-surface p-6 lg:p-8">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-black uppercase tracking-wide text-brand-700">Centro de Compras Autonomo</p>
          <h1 className="mt-1 text-2xl font-black text-stone-900">Plano de compra Maestro</h1>
          <p className="mt-1 text-sm font-semibold text-stone-500">
            {plan
              ? `Plano #${plan.id} · ${fmt.date(plan.date_from)} a ${fmt.date(plan.date_to)} · ${plan.status}`
              : `Sugestao baseada no consumo dos ultimos ${horizonDays} dias para estimar os proximos ${horizonDays} dias.`}
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
        <PlanEmptyState
          onGenerate={handleGenerate}
          pending={generate.isPending}
          horizonDays={horizonDays}
        />
      ) : (
        <div className="space-y-6">
          <section className="rounded-xl border border-brand-100 bg-brand-50 px-5 py-4 text-sm font-semibold leading-relaxed text-stone-700">
            Esta sugestao considera o consumo dos ultimos {plan.horizon_days} dias para estimar
            a necessidade dos proximos {plan.horizon_days} dias. Itens sem consumo nesse periodo
            nao recebem compra artificial.
          </section>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <KpiCard icon={ShoppingCart} label="Custo estimado" value={fmt.currency(plan.approved_total || plan.total_estimated)} detail={`${plan.items.length} itens no plano`} />
            <KpiCard icon={ShieldAlert} label="Itens criticos" value={String(plan.critical_items_count)} detail="Prioridade de revisao" tone="red" />
            <KpiCard icon={Timer} label="Cobertura media" value={`${plan.avg_coverage_days.toLocaleString('pt-BR', { maximumFractionDigits: 1 })} dias`} detail={`Horizonte de ${plan.horizon_days} dias`} tone="blue" />
            <KpiCard icon={PiggyBank} label="Economia potencial" value={fmt.currency(plan.savings_potential)} detail="Comparacao com menor preco viavel" tone="green" />
          </div>

          <section className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-stone-200 bg-white p-3">
            <div>
              <p className="text-xs font-black uppercase tracking-wide text-stone-500">Visualizacao do plano</p>
              <p className="mt-1 text-sm font-semibold text-stone-600">
                Revise os itens antes de enviar cotacoes e aprovar os pedidos.
              </p>
            </div>
            <div className="inline-flex rounded-lg border border-stone-200 bg-stone-50 p-1">
              {([
                ['items', 'Itens recomendados'],
                ['quotes', 'Cotacoes e aprovacao'],
              ] as Array<[PlanView, string]>).map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setView(value)}
                  disabled={hasPendingItemChange}
                  className={cn(
                    'rounded-md px-4 py-2 text-sm font-black transition disabled:cursor-not-allowed disabled:opacity-50',
                    view === value ? 'bg-white text-brand-700' : 'text-stone-500 hover:text-stone-800',
                  )}
                >
                  {label}
                </button>
              ))}
            </div>
          </section>

          {view === 'items' ? (
            <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
              <PurchasePlanTable
                plan={plan}
                items={visibleItems}
                selectedItemId={selectedItem?.ingredient_id}
                setSelectedItemId={setSelectedItemId}
                quantities={quantities}
                suppliers={suppliers}
                setQuantities={setQuantities}
                setSuppliers={setSuppliers}
                onQuantityBlur={handleQuantityBlur}
                onSupplierChange={handleSupplierChange}
                onDelete={handleDelete}
                savingKey={savingKey}
                deletingKey={deletingKey}
                page={currentPage}
                pageSize={pageSize}
                totalPages={totalPages}
                onPageChange={setPage}
                onPageSizeChange={value => {
                  setPageSize(value)
                  setPage(1)
                }}
              />
              <SupplierPanel item={selectedItem} />
            </div>
          ) : (
            <section className="rounded-xl border border-stone-200 bg-white p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <h2 className="text-base font-black text-stone-900">Cotacoes e aprovacao</h2>
                  <p className="mt-1 text-sm font-semibold text-stone-500">
                    Emails corporativos por fornecedor e criacao de pedidos em transito.
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={handleSendQuotes}
                    disabled={isBusy || plan.status === 'aprovado'}
                    className="inline-flex items-center gap-2 rounded-lg border border-stone-200 bg-white px-4 py-2 text-sm font-black text-stone-800 transition hover:border-brand-300 hover:text-brand-700 disabled:opacity-60"
                  >
                    <Mail className="size-4" strokeWidth={2.1} />
                    {sendQuotes.isPending ? 'Enviando...' : 'Enviar cotacoes'}
                  </button>
                  <button
                    type="button"
                    onClick={handleApprove}
                    disabled={isBusy || plan.status === 'aprovado'}
                    className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-black text-white transition hover:bg-brand-700 disabled:opacity-60"
                  >
                    <CheckCircle2 className="size-4" strokeWidth={2.1} />
                    {approve.isPending ? 'Aprovando...' : plan.status === 'aprovado' ? 'Plano aprovado' : 'Aprovar pedidos'}
                  </button>
                </div>
              </div>
              {plan.quotes.length > 0 ? (
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
              ) : (
                <p className="mt-5 rounded-lg border border-dashed border-stone-200 bg-stone-50 p-8 text-center text-sm font-bold text-stone-500">
                  Nenhuma cotacao disponivel para os itens atuais.
                </p>
              )}
            </section>
          )}
        </div>
      )}
    </main>
  )
}
