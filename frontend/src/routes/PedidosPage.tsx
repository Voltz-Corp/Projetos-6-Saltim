import { useMemo, useState, type ComponentType, type ReactNode } from 'react'
import { createRoute, Link, useNavigate } from '@tanstack/react-router'
import {
  AlertTriangle,
  ArrowLeft,
  CalendarClock,
  CalendarDays,
  Check,
  ChevronDown,
  CircleDollarSign,
  ClipboardList,
  Hash,
  Minus,
  Package,
  PackageCheck,
  Plus,
  Search,
  Store,
  Trash2,
  Truck,
} from 'lucide-react'
import { rootRoute } from './Root'
import { AppSelect } from '../components/AppSelect'
import { DataTable, type DataTableHeader } from '../components/DataTable'
import { ExportPanel } from '../components/ExportPanel'
import { KpiCard } from '../components/KpiCard'
import {
  DateFilterControl,
  type DateFilterMode,
} from '../components/DateFilterControl'
import { FilterDrawer, FilterField, FilterSection } from '../components/FilterPanel'
import { useFornecedores } from '../hooks/useFornecedores'
import { useEstoque, type StockItem } from '../hooks/useEstoque'
import {
  useCreatePedido,
  usePedidoGroupDetail,
  usePedidoRecommendation,
  usePedidos,
  usePedidosEmTransito,
  type PedidoDetailItem,
  type PedidoEmailResult,
  type PedidoFilters,
  type PedidoGroup,
  type PedidoRecommendationItem,
  useMarkPedidoGroupDelivered,
} from '../hooks/usePedidos'

export const pedidosRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/pedidos',
  component: PedidosPage,
})

export const pedidoNewRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/pedidos/novo',
  component: PedidoNewPage,
})

export const pedidoGroupDetailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/pedidos/grupos/$supplierId/$orderDate',
  component: PedidoGroupDetailPage,
})

type OrdersView = 'history' | 'transit'
type OrderStep = 'selection' | 'review'

interface SelectedIngredient {
  ingredient: StockItem
  qty: string
}

const PAGE_SIZE_OPTIONS = [10, 25, 50]
const STATUS_OPTIONS = [
  { value: '', label: 'Todos os status' },
  { value: 'entregue', label: 'Entregue' },
]

const fmt = {
  number: (value: number, digits = 2) =>
    value.toLocaleString('pt-BR', {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    }),
  currency: (value: number) =>
    value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }),
  date: (value: string) =>
    new Date(`${value}T00:00:00`).toLocaleDateString('pt-BR'),
  percent: (value: number) =>
    `${(value * 100).toLocaleString('pt-BR', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 1,
    })}%`,
}

function todayISO() {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Recife',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date())
}

function isDeliveryDue(expectedDate: string) {
  return expectedDate <= todayISO()
}

function PedidosPage() {
  const [view, setView] = useState<OrdersView>('history')
  const [status, setStatus] = useState('')
  const [supplierId, setSupplierId] = useState('')
  const [dateMode, setDateMode] = useState<DateFilterMode>('all')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [draftStatus, setDraftStatus] = useState('')
  const [draftSupplierId, setDraftSupplierId] = useState('')
  const [draftDateMode, setDraftDateMode] = useState<DateFilterMode>('all')
  const [draftDateFrom, setDraftDateFrom] = useState('')
  const [draftDateTo, setDraftDateTo] = useState('')
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)

  const filters: PedidoFilters = {
    status: status || undefined,
    supplierId: supplierId || undefined,
    dateFrom: dateMode === 'all' ? undefined : dateFrom || undefined,
    dateTo: dateMode === 'all' ? undefined : dateTo || undefined,
    page,
    pageSize,
  }
  const transitFilters: PedidoFilters = {
    supplierId: supplierId || undefined,
    dateFrom: dateMode === 'all' ? undefined : dateFrom || undefined,
    dateTo: dateMode === 'all' ? undefined : dateTo || undefined,
  }

  const { data: fornecedores } = useFornecedores()
  const { data, isFetching, isError } = usePedidos(filters)
  const { data: inTransit = [], isFetching: isFetchingTransit } =
    usePedidosEmTransito(transitFilters)
  const markDelivered = useMarkPedidoGroupDelivered()

  const supplierOptions = [
    { value: '', label: 'Todos os fornecedores' },
    ...(fornecedores?.items ?? []).map((supplier) => ({
      value: supplier.id,
      label: supplier.name,
    })),
  ]

  const appliedFilterCount = [
    view === 'history' ? status : '',
    supplierId,
    dateMode !== 'all' && (dateFrom || dateTo) ? 'date' : '',
  ].filter(Boolean).length

  function applyFilters() {
    setStatus(draftStatus)
    setSupplierId(draftSupplierId)
    setDateMode(draftDateMode)
    setDateFrom(draftDateFrom)
    setDateTo(draftDateTo)
    setPage(1)
    setFiltersOpen(false)
  }

  function clearFilters() {
    setStatus('')
    setSupplierId('')
    setDateMode('all')
    setDateFrom('')
    setDateTo('')
    setDraftStatus('')
    setDraftSupplierId('')
    setDraftDateMode('all')
    setDraftDateFrom('')
    setDraftDateTo('')
    setPage(1)
    setFiltersOpen(false)
  }

  const items = data?.items ?? []
  const activeTotal = view === 'history' ? data?.total ?? 0 : inTransit.length
  const dueTransit = inTransit.filter((pedido) => isDeliveryDue(pedido.expected_date))
  const dueTransitQty = dueTransit.reduce((total, pedido) => total + pedido.items_qty, 0)

  return (
    <div className="flex h-screen flex-col bg-surface">
      <header className="flex h-[73px] flex-shrink-0 items-center justify-between border-b border-stone-200 bg-white px-8">
        <div>
          <h1 className="text-xl font-semibold text-stone-900">Pedidos</h1>
          <p className="mt-1 text-xs tabular-nums text-stone-400">
            {isFetching || isFetchingTransit
              ? 'Carregando...'
              : `${activeTotal} grupos de pedidos encontrados`}
          </p>
        </div>
        <Link
          to="/pedidos/novo"
          className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-bold text-white transition hover:bg-brand-700"
        >
          <Plus className="size-4" strokeWidth={2} />
          Novo pedido
        </Link>
      </header>

      <FilterDrawer
        title="Filtros de pedidos"
        subtitle="Aplicados à tabela selecionada"
        open={filtersOpen}
        onOpen={() => setFiltersOpen(true)}
        onClose={() => setFiltersOpen(false)}
        onApply={applyFilters}
        onClear={clearFilters}
        appliedCount={appliedFilterCount}
      >
        <FilterSection title="Pedido">
          {view === 'history' && (
            <FilterField label="Status">
              <AppSelect
                value={draftStatus}
                onChange={setDraftStatus}
                options={STATUS_OPTIONS}
                className="w-full"
              />
            </FilterField>
          )}
          <FilterField label="Fornecedor">
            <AppSelect
              value={draftSupplierId}
              onChange={setDraftSupplierId}
              options={supplierOptions}
              className="w-full"
            />
          </FilterField>
        </FilterSection>

        <FilterSection title="Tempo" defaultOpen={false}>
          <FilterField label="Data do pedido">
            <DateFilterControl
              mode={draftDateMode}
              dateFrom={draftDateFrom}
              dateTo={draftDateTo}
              onChange={(value) => {
                setDraftDateMode(value.mode)
                setDraftDateFrom(value.dateFrom)
                setDraftDateTo(value.dateTo)
              }}
            />
          </FilterField>
        </FilterSection>
      </FilterDrawer>

      <main className="flex-1 space-y-6 overflow-auto p-6">
        <section className="rounded-xl border border-stone-200 bg-white p-4 shadow-sm">
          <SegmentedToggle value={view} onChange={setView} />
        </section>

        <ExportPanel
          area="pedidos"
          title="Exportar historico de pedidos"
          subtitle="Baixe os pedidos realizados dentro do periodo selecionado."
          requiresDateRange
        />

        {view === 'transit' && dueTransit.length > 0 && (
          <section className="saltim-alert flex flex-col gap-4 rounded-lg border px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex min-w-0 items-start gap-3">
              <span className="saltim-alert-icon flex size-10 flex-shrink-0 items-center justify-center rounded-lg">
                <AlertTriangle className="size-5" strokeWidth={2} />
              </span>
              <div className="min-w-0">
                <p className="text-sm font-black">Entregas aguardando recebimento</p>
                <p className="mt-1 text-xs font-semibold leading-5">
                  {dueTransit.length} pedido{dueTransit.length === 1 ? '' : 's'} com previsao vencida ou para hoje. Ao marcar como entregue, os ingredientes entram no estoque atual.
                </p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2 text-center sm:w-56">
              <span className="rounded-lg bg-white px-3 py-2">
                <span className="block text-lg font-black">{dueTransit.length}</span>
                <span className="text-[11px] font-bold uppercase text-stone-400">pedidos</span>
              </span>
              <span className="rounded-lg bg-white px-3 py-2">
                <span className="block text-lg font-black">{fmt.number(dueTransitQty, 2)}</span>
                <span className="text-[11px] font-bold uppercase text-stone-400">itens</span>
              </span>
            </div>
          </section>
        )}

        <DataPanel
          title={view === 'history' ? 'Histórico por fornecedor e dia' : 'Pedidos em trânsito'}
          subtitle={
            view === 'history'
              ? 'Pedidos agrupados por fornecedor e data'
              : 'Pedidos em aberto agrupados por fornecedor e data'
          }
        >
          {view === 'history' ? (
            <PedidosTable
              pedidos={items}
              isLoading={isFetching}
              isError={isError}
              showExpectedDate={false}
              pagination={{
                page,
                pageSize,
                total: data?.total ?? 0,
                totalPages: data?.total_pages ?? 1,
                pageSizeOptions: PAGE_SIZE_OPTIONS,
                onPageChange: setPage,
                onPageSizeChange: (value) => {
                  setPageSize(value)
                  setPage(1)
                },
              }}
            />
          ) : (
            <PedidosTable
              pedidos={inTransit}
              isLoading={isFetchingTransit}
              emptyMessage="Nenhum pedido em trânsito."
              showExpectedDate
              deliveringGroupKey={
                markDelivered.isPending
                  ? `${markDelivered.variables?.supplierId}-${markDelivered.variables?.orderDate}`
                  : undefined
              }
              onMarkDelivered={(pedido) =>
                markDelivered.mutate({
                  supplierId: pedido.supplier_id,
                  orderDate: pedido.order_date,
                })
              }
            />
          )}
        </DataPanel>
      </main>
    </div>
  )
}

function PedidoNewPage() {
  const navigate = useNavigate()
  const { data: ingredients = [] } = useEstoque()
  const recommendPedido = usePedidoRecommendation()
  const createPedido = useCreatePedido()
  const [step, setStep] = useState<OrderStep>('selection')
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<SelectedIngredient[]>([])
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set())
  const [recommendation, setRecommendation] = useState<PedidoRecommendationItem[]>([])
  const [supplierByIngredient, setSupplierByIngredient] = useState<Record<string, string>>({})
  const [error, setError] = useState('')
  const [emailNotice, setEmailNotice] = useState('')
  const [confirmed, setConfirmed] = useState(false)

  const selectedIds = useMemo(
    () => new Set(selected.map((item) => String(item.ingredient.id))),
    [selected],
  )

  const available = useMemo(
    () =>
      ingredients.filter(
        (ingredient) =>
          !selectedIds.has(String(ingredient.id)) &&
          ingredient.name.toLowerCase().includes(search.toLowerCase()),
      ),
    [ingredients, search, selectedIds],
  )

  const groupedAvailable = useMemo(() => {
    const groups = new Map<string, StockItem[]>()
    available.forEach((ingredient) => {
      const category = ingredient.category || 'Sem categoria'
      groups.set(category, [...(groups.get(category) ?? []), ingredient])
    })
    return Array.from(groups.entries()).sort(([a], [b]) => a.localeCompare(b))
  }, [available])

  const canReview =
    selected.length > 0 && selected.every((item) => Number(item.qty) > 0)

  const reviewGroups = useMemo(
    () => buildReviewGroups(recommendation, supplierByIngredient),
    [recommendation, supplierByIngredient],
  )
  const reviewTotal = reviewGroups.reduce((sum, group) => sum + group.totalValue, 0)
  const unresolvedItems = recommendation.filter(
    (item) => !supplierByIngredient[item.ingredient_id],
  )

  function addIngredient(ingredient: StockItem) {
    setSelected((current) => [...current, { ingredient, qty: '1' }])
  }

  function removeIngredient(id: string | number) {
    setSelected((current) =>
      current.filter((item) => String(item.ingredient.id) !== String(id)),
    )
  }

  function updateQty(id: string | number, qty: string) {
    setSelected((current) =>
      current.map((item) =>
        String(item.ingredient.id) === String(id) ? { ...item, qty } : item,
      ),
    )
  }

  function adjustQty(id: string | number, delta: number) {
    setSelected((current) =>
      current.map((item) => {
        if (String(item.ingredient.id) !== String(id)) return item
        const currentQty = Number(item.qty) || 0
        const nextQty = Math.max(0, Math.round((currentQty + delta) * 100) / 100)
        return { ...item, qty: String(nextQty) }
      }),
    )
  }

  function toggleCategory(category: string) {
    setExpandedCategories((current) => {
      const next = new Set(current)
      if (next.has(category)) next.delete(category)
      else next.add(category)
      return next
    })
  }

  async function handleReview() {
    setError('')
    setEmailNotice('')
    setConfirmed(false)
    try {
      const response = await recommendPedido.mutateAsync({
        items: selected.map((item) => ({
          ingredient_id: String(item.ingredient.id),
          qty: Number(item.qty),
        })),
      })
      setRecommendation(response.items)
      setSupplierByIngredient(
        Object.fromEntries(
          response.items
            .filter((item) => item.recommended_supplier_id)
            .map((item) => [item.ingredient_id, item.recommended_supplier_id as string]),
        ),
      )
      setStep('review')
    } catch {
      setError('Não foi possível calcular os fornecedores.')
    }
  }

  async function handleConfirm() {
    setError('')
    setEmailNotice('')
    try {
      const response = await createPedido.mutateAsync({
        items: recommendation
          .filter((item) => supplierByIngredient[item.ingredient_id])
          .map((item) => ({
            ingredient_id: item.ingredient_id,
            qty: item.qty,
            supplier_id: supplierByIngredient[item.ingredient_id],
          })),
      })
      const emailIssues = (response.email_results ?? []).filter(
        (result) => result.status !== 'sent',
      )
      if (emailIssues.length > 0) {
        setConfirmed(true)
        setEmailNotice(formatEmailNotice(emailIssues))
        return
      }
      navigate({ to: '/pedidos' })
    } catch {
      setError('Não foi possível confirmar os pedidos.')
    }
  }

  return (
    <div className="flex h-screen flex-col bg-surface">
      <header className="flex h-[73px] flex-shrink-0 items-center gap-3 border-b border-stone-200 bg-white px-8">
        <button
          type="button"
          onClick={() => (step === 'review' ? setStep('selection') : navigate({ to: '/pedidos' }))}
          className="flex size-9 items-center justify-center rounded-lg border border-stone-200 text-stone-500 transition hover:bg-stone-50 hover:text-stone-900"
          aria-label="Voltar"
        >
          <ArrowLeft className="size-4" strokeWidth={2} />
        </button>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-bold uppercase tracking-wide text-brand-600">
            Novo pedido
          </p>
          <h1 className="truncate text-xl font-semibold text-stone-900">
            {step === 'selection' ? 'Selecionar ingredientes' : 'Revisar fornecedores'}
          </h1>
        </div>
      </header>

      <main className="flex-1 overflow-auto p-6">
        <div className="space-y-6">
          <StepBar step={step} />

          {error && (
            <section className="saltim-danger-soft rounded-xl border px-4 py-3 text-sm font-semibold">
              {error}
            </section>
          )}

          {emailNotice && (
            <section className="saltim-alert rounded-xl border px-4 py-3 text-sm font-semibold">
              {emailNotice}
            </section>
          )}

          {step === 'selection' ? (
            <>
              <section className="grid grid-cols-1 items-start gap-6 xl:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.65fr)]">
                <IngredientList
                  title="Ingredientes disponíveis"
                  subtitle="Selecione o que deseja comprar"
                  search={search}
                  onSearchChange={setSearch}
                  variant="available"
                >
                  {groupedAvailable.length === 0 ? (
                    <EmptyState>Nenhum ingrediente encontrado.</EmptyState>
                  ) : (
                    groupedAvailable.map(([category, items]) => {
                      const expanded = expandedCategories.has(category)
                      return (
                        <section key={category} className="border-b border-stone-100 last:border-0">
                          <button
                            type="button"
                            onClick={() => toggleCategory(category)}
                            className="flex w-full items-center justify-between gap-4 bg-stone-50/80 px-5 py-4 text-left transition hover:bg-stone-100"
                          >
                            <span className="flex min-w-0 items-center gap-3">
                              <span className="flex size-10 flex-shrink-0 items-center justify-center rounded-lg bg-white text-brand-700 shadow-sm">
                                <ClipboardList className="size-5" strokeWidth={2} />
                              </span>
                              <span className="min-w-0">
                                <span className="block truncate text-base font-black text-stone-900">
                                  {category}
                                </span>
                                <span className="mt-1 inline-flex items-center gap-1 text-xs font-bold text-stone-500">
                                  <Hash className="size-3.5" strokeWidth={2} />
                                  {items.length} ingrediente{items.length !== 1 ? 's' : ''}
                                </span>
                              </span>
                            </span>
                            <ChevronDown
                              className={[
                                'size-4 text-stone-400 transition-transform',
                                expanded ? 'rotate-180' : '',
                              ].join(' ')}
                              strokeWidth={2}
                            />
                          </button>
                          {expanded &&
                            items.map((ingredient) => (
                              <button
                                key={ingredient.id}
                                type="button"
                                onClick={() => addIngredient(ingredient)}
                                className="ml-6 flex w-[calc(100%-1.5rem)] items-center justify-between gap-3 border-t border-stone-100 px-4 py-3 text-left transition hover:bg-brand-50/40"
                              >
                                <div className="flex min-w-0 items-center gap-3">
                                  <span className="flex size-8 flex-shrink-0 items-center justify-center rounded-lg bg-stone-100 text-stone-500">
                                    <Package className="size-4" strokeWidth={2} />
                                  </span>
                                  <span className="min-w-0">
                                    <span className="block truncate text-sm font-bold text-stone-900">
                                      {ingredient.name}
                                    </span>
                                    <span className="block text-xs text-stone-400">
                                      {ingredient.category} · {ingredient.unit}
                                    </span>
                                  </span>
                                </div>
                                <Plus className="size-4 flex-shrink-0 text-brand-600" />
                              </button>
                            ))}
                        </section>
                      )
                    })
                  )}
                </IngredientList>

                <IngredientList
                  title="Lista de compra"
                  subtitle={`${selected.length} ingrediente${selected.length !== 1 ? 's' : ''} selecionado${selected.length !== 1 ? 's' : ''}`}
                  variant="cart"
                >
                  {selected.length === 0 ? (
                    <EmptyState>Nenhum ingrediente selecionado.</EmptyState>
                  ) : (
                    selected.map(({ ingredient, qty }) => (
                      <div
                        key={ingredient.id}
                        className="grid grid-cols-[minmax(0,1fr)_120px_32px] items-center gap-2 border-b border-brand-100/70 px-3 py-2.5 last:border-0"
                      >
                        <div className="flex min-w-0 items-center gap-2">
                          <span className="flex size-7 flex-shrink-0 items-center justify-center rounded-lg bg-white text-brand-700 shadow-sm">
                            <Package className="size-3.5" strokeWidth={2} />
                          </span>
                          <span className="min-w-0">
                            <span className="block truncate text-sm font-black text-stone-900">
                              {ingredient.name}
                            </span>
                            <span className="block truncate text-[11px] text-stone-500">
                              {ingredient.unit}
                            </span>
                          </span>
                        </div>
                        <QtyStepper
                          value={qty}
                          unit={ingredient.unit}
                          onChange={(value) => updateQty(ingredient.id, value)}
                          onDecrease={() => adjustQty(ingredient.id, -1)}
                          onIncrease={() => adjustQty(ingredient.id, 1)}
                        />
                        <button
                          type="button"
                          onClick={() => removeIngredient(ingredient.id)}
                          className="flex size-8 items-center justify-center rounded-lg text-stone-400 transition hover:bg-stone-100 hover:text-saltim-red"
                          aria-label="Remover ingrediente"
                        >
                          <Trash2 className="size-4" strokeWidth={2} />
                        </button>
                      </div>
                    ))
                  )}
                </IngredientList>
              </section>

              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => navigate({ to: '/pedidos' })}
                  className="rounded-lg border border-stone-200 px-4 py-2 text-sm font-bold text-stone-600 transition hover:bg-stone-50"
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  disabled={!canReview || recommendPedido.isPending}
                  onClick={handleReview}
                  className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-bold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {recommendPedido.isPending ? 'Calculando...' : 'Revisar fornecedores'}
                </button>
              </div>
            </>
          ) : (
            <>
              <section className="grid grid-cols-1 gap-4 md:grid-cols-3">
                <KpiCard
                  icon={PackageCheck}
                  label="Ingredientes"
                  value={fmt.number(recommendation.length, 0)}
                  detail="Itens na lista"
                  tone="green"
                />
                <KpiCard
                  icon={Truck}
                  label="Fornecedores"
                  value={fmt.number(reviewGroups.length, 0)}
                  detail="Pedidos a confirmar"
                  tone="orange"
                />
                <KpiCard
                  icon={CircleDollarSign}
                  label="Total estimado"
                  value={fmt.currency(reviewTotal)}
                  detail="Com descontos aplicados"
                  tone="blue"
                />
              </section>

              <section className="space-y-4">
                {recommendation.map((item) => (
                  <ReviewItem
                    key={item.ingredient_id}
                    item={item}
                    selectedSupplierId={supplierByIngredient[item.ingredient_id] ?? ''}
                    onChange={(supplierId) =>
                      setSupplierByIngredient((current) => ({
                        ...current,
                        [item.ingredient_id]: supplierId,
                      }))
                    }
                  />
                ))}
              </section>

              <DataPanel
                title="Pedidos gerados"
                subtitle="Agrupamento previsto por fornecedor"
              >
                <ReviewGroupsTable groups={reviewGroups} />
              </DataPanel>

              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setStep('selection')}
                  className="rounded-lg border border-stone-200 px-4 py-2 text-sm font-bold text-stone-600 transition hover:bg-stone-50"
                >
                  Voltar
                </button>
                <button
                  type="button"
                  disabled={
                    createPedido.isPending ||
                    confirmed ||
                    recommendation.length === 0 ||
                    unresolvedItems.length > 0
                  }
                  onClick={handleConfirm}
                  className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-bold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {createPedido.isPending ? 'Confirmando...' : 'Confirmar pedidos'}
                </button>
                {confirmed && (
                  <button
                    type="button"
                    onClick={() => navigate({ to: '/pedidos' })}
                    className="rounded-lg bg-stone-900 px-4 py-2 text-sm font-bold text-white transition hover:bg-stone-800"
                  >
                    Ir para pedidos
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      </main>
    </div>
  )
}

function PedidoGroupDetailPage() {
  const navigate = useNavigate()
  const { supplierId, orderDate } = pedidoGroupDetailRoute.useParams()
  const { data, isFetching, isError } = usePedidoGroupDetail(supplierId, orderDate)
  const markDelivered = useMarkPedidoGroupDelivered()

  async function handleMarkDelivered() {
    await markDelivered.mutateAsync({ supplierId, orderDate })
  }

  return (
    <div className="flex h-screen flex-col bg-surface">
      <header className="flex h-[73px] flex-shrink-0 items-center gap-3 border-b border-stone-200 bg-white px-8">
        <button
          type="button"
          onClick={() => navigate({ to: '/pedidos' })}
          className="flex size-9 items-center justify-center rounded-lg border border-stone-200 text-stone-500 transition hover:bg-stone-50 hover:text-stone-900"
          aria-label="Voltar"
        >
          <ArrowLeft className="size-4" strokeWidth={2} />
        </button>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-bold uppercase tracking-wide text-brand-600">
            Pedido por fornecedor e dia
          </p>
          <h1 className="truncate text-xl font-semibold text-stone-900">
            {data ? `${data.supplier_name} · ${fmt.date(data.order_date)}` : 'Pedido'}
          </h1>
        </div>
        {data && (data.status === 'em_transito' || !data.stock_applied_at) && (
          <button
            type="button"
            onClick={handleMarkDelivered}
            disabled={markDelivered.isPending}
            className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-bold text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <PackageCheck className="size-4" strokeWidth={2} />
            {markDelivered.isPending
              ? 'Atualizando...'
              : data.status === 'em_transito'
                ? 'Marcar como entregue'
                : 'Aplicar no estoque'}
          </button>
        )}
      </header>

      <main className="flex-1 space-y-6 overflow-auto p-6">
        {isFetching ? (
          <EmptyPanel>Carregando pedido...</EmptyPanel>
        ) : isError || !data ? (
          <EmptyPanel>Pedido não encontrado.</EmptyPanel>
        ) : (
          <>
            <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
              <KpiCard icon={Store} label="Fornecedor" value={data.supplier_name} tone="orange" truncateValue />
              <KpiCard icon={CalendarDays} label="Data do pedido" value={fmt.date(data.order_date)} tone="blue" />
              <KpiCard icon={CalendarClock} label="Previsão" value={fmt.date(data.expected_date)} tone="cream" />
              <KpiCard
                icon={PackageCheck}
                label="Status"
                value={formatStatus(data.status)}
                tone={data.status === 'entregue' ? 'green' : 'orange'}
                badgeValue
                badgeTone={data.status === 'entregue' ? 'green' : 'amber'}
              />
            </section>

            <section className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
              <DataPanel
                title="Ingredientes do pedido"
                subtitle={`${data.items.length} ingrediente${data.items.length !== 1 ? 's' : ''} no grupo`}
              >
                <PedidoItemsTable items={data.items} />
              </DataPanel>

              <aside className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
                <p className="text-sm font-black text-stone-900">Resumo do pedido</p>
                <p className="mt-1 text-xs text-stone-400">
                  Totais agrupados por fornecedor e dia
                </p>
                <div className="mt-5 space-y-3">
                  <SummaryMetric
                    icon={Hash}
                    label="Quantidade total"
                    value={fmt.number(data.items_qty, 2)}
                  />
                  <SummaryMetric
                    icon={CircleDollarSign}
                    label="Total do pedido"
                    value={fmt.currency(data.total_value)}
                    featured
                  />
                </div>
              </aside>
            </section>
          </>
        )}
      </main>
    </div>
  )
}

function SegmentedToggle({
  value,
  onChange,
}: {
  value: OrdersView
  onChange: (value: OrdersView) => void
}) {
  return (
    <div className="grid w-full max-w-md grid-cols-2 rounded-full bg-stone-100 p-1">
      {[
        ['history', 'Histórico de pedidos'],
        ['transit', 'Pedidos em trânsito'],
      ].map(([key, label]) => (
        <button
          key={key}
          type="button"
          onClick={() => onChange(key as OrdersView)}
          className={[
            'rounded-full px-3 py-1.5 text-xs font-black transition',
            value === key
              ? 'bg-white text-stone-950 shadow-sm'
              : 'text-stone-600 hover:text-stone-900',
          ].join(' ')}
        >
          {label}
        </button>
      ))}
    </div>
  )
}

function StepBar({ step }: { step: OrderStep }) {
  return (
    <section className="rounded-xl border border-stone-200 bg-white p-4 shadow-sm">
      <div className="grid gap-3 sm:grid-cols-2">
        {[
          ['selection', 'Selecionar ingredientes'],
          ['review', 'Revisar fornecedores'],
        ].map(([key, label], index) => {
          const active = step === key
          const complete = step === 'review' && key === 'selection'
          return (
            <div
              key={key}
              className={[
                'flex items-center gap-3 rounded-lg border px-4 py-3',
                active || complete
                  ? 'border-brand-100 bg-brand-50 text-brand-800'
                  : 'border-stone-100 bg-stone-50 text-stone-500',
              ].join(' ')}
            >
              <span
                className={[
                  'flex size-7 items-center justify-center rounded-full text-xs font-black',
                  active || complete ? 'bg-white text-brand-700' : 'bg-white text-stone-400',
                ].join(' ')}
              >
                {complete ? <Check className="size-4" /> : index + 1}
              </span>
              <span className="text-sm font-black">{label}</span>
            </div>
          )
        })}
      </div>
    </section>
  )
}

function ReviewItem({
  item,
  selectedSupplierId,
  onChange,
}: {
  item: PedidoRecommendationItem
  selectedSupplierId: string
  onChange: (supplierId: string) => void
}) {
  const selectedOption = item.options.find(
    (option) => option.supplier_id === selectedSupplierId,
  )
  const supplierOptions = item.options.map((option) => ({
    value: option.supplier_id,
    label: `${option.supplier_name} · ${fmt.currency(option.total_value)}`,
  }))

  return (
    <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px] xl:items-start">
        <div className="min-w-0">
          <p className="truncate text-sm font-black text-stone-900">
            {item.ingredient_name}
          </p>
          <p className="mt-1 text-xs text-stone-400">
            {item.category} · {fmt.number(item.qty, 2)} {item.unit}
          </p>
          {selectedOption ? (
            <div className="mt-3 flex flex-wrap gap-2 text-xs">
              <MetricPill label="Preço" value={fmt.currency(selectedOption.effective_unit_price)} />
              <MetricPill label="Total" value={fmt.currency(selectedOption.total_value)} />
              <MetricPill label="Entrega" value={`${selectedOption.delivery_time_days} dia${selectedOption.delivery_time_days === 1 ? '' : 's'}`} />
              {selectedOption.discount_applied && (
                <MetricPill label="Desconto" value={fmt.percent(selectedOption.discount_percent)} />
              )}
            </div>
          ) : (
            <p className="mt-3 text-xs font-semibold text-saltim-red">
              Nenhum fornecedor disponível para este ingrediente.
            </p>
          )}
          {selectedOption && !selectedOption.recommended && (
            <p className="mt-3 text-xs font-semibold text-[var(--theme-alert-strong)]">
              {selectedOption.detractors.length > 0
                ? `Detrator: ${selectedOption.detractors.join(', ')}.`
                : 'Fornecedor alternativo sem detrator relevante.'}
            </p>
          )}
        </div>

        <AppSelect
          value={selectedSupplierId}
          onChange={onChange}
          options={supplierOptions}
          className="w-full"
        />
      </div>
    </section>
  )
}

function ReviewGroupsTable({
  groups,
}: {
  groups: Array<{
    supplierId: string
    supplierName: string
    expectedDate: string
    totalValue: number
    items: Array<{ ingredientName: string; qty: number; unit: string }>
  }>
}) {
  return (
    <DataTable
      headers={reviewGroupHeaders}
      colSpan={5}
      minWidth="860px"
      isEmpty={groups.length === 0}
      emptyMessage="Nenhum pedido para confirmar."
      embedded
    >
      {groups.map((group) => (
        <tr
          key={group.supplierId}
          className="border-b border-stone-100 transition-colors last:border-0 hover:bg-stone-50"
        >
          <BodyCell strong>{group.supplierName}</BodyCell>
          <BodyCell>{group.items.length}</BodyCell>
          <BodyCell>{fmt.date(group.expectedDate)}</BodyCell>
          <BodyCell>
            {group.items.slice(0, 2).map((item) => item.ingredientName).join(', ')}
            {group.items.length > 2 ? ` +${group.items.length - 2}` : ''}
          </BodyCell>
          <BodyCell align="right">{fmt.currency(group.totalValue)}</BodyCell>
        </tr>
      ))}
    </DataTable>
  )
}

function SummaryMetric({
  icon: Icon,
  label,
  value,
  featured = false,
}: {
  icon: ComponentType<{ className?: string; strokeWidth?: number }>
  label: string
  value: string
  featured?: boolean
}) {
  return (
    <div
      className={[
        'flex items-center gap-3 rounded-xl border p-4',
        featured
          ? 'border-brand-100 bg-brand-50'
          : 'border-stone-100 bg-stone-50',
      ].join(' ')}
    >
      <span
        className={[
          'flex size-10 items-center justify-center rounded-xl',
          featured ? 'bg-white text-brand-700' : 'bg-white text-stone-500',
        ].join(' ')}
      >
        <Icon className="size-5" strokeWidth={2} />
      </span>
      <span className="min-w-0">
        <span
          className={[
            'block text-[11px] font-black uppercase tracking-wide',
            featured ? 'text-brand-700' : 'text-stone-400',
          ].join(' ')}
        >
          {label}
        </span>
        <span className="mt-1 block truncate text-xl font-black tabular-nums text-stone-900">
          {value}
        </span>
      </span>
    </div>
  )
}

function PedidoItemsTable({ items }: { items: PedidoDetailItem[] }) {
  return (
    <DataTable
      headers={pedidoItemHeaders}
      colSpan={6}
      minWidth="860px"
      isEmpty={items.length === 0}
      emptyMessage="Nenhum ingrediente registrado neste pedido."
      embedded
    >
      {items.map((item) => (
        <tr
          key={item.ingredient_id}
          className="border-b border-stone-100 transition-colors last:border-0 hover:bg-stone-50"
        >
          <BodyCell strong>{item.ingredient_name}</BodyCell>
          <BodyCell>{item.category}</BodyCell>
          <BodyCell>{item.unit}</BodyCell>
          <BodyCell align="right">{fmt.number(item.qty, 2)}</BodyCell>
          <BodyCell align="right">{fmt.currency(item.unit_price)}</BodyCell>
          <BodyCell align="right">{fmt.currency(item.total_value)}</BodyCell>
        </tr>
      ))}
    </DataTable>
  )
}

function DataPanel({
  title,
  subtitle,
  children,
}: {
  title: string
  subtitle: string
  children: ReactNode
}) {
  return (
    <section className="overflow-hidden rounded-xl border border-stone-200 bg-white">
      <div className="border-b border-stone-100 px-5 py-4">
        <h2 className="text-sm font-black text-stone-900">{title}</h2>
        <p className="mt-1 text-xs text-stone-400">{subtitle}</p>
      </div>
      {children}
    </section>
  )
}

function QtyStepper({
  value,
  unit,
  onChange,
  onDecrease,
  onIncrease,
}: {
  value: string
  unit: string
  onChange: (value: string) => void
  onDecrease: () => void
  onIncrease: () => void
}) {
  return (
    <div className="grid grid-cols-[28px_minmax(0,1fr)_28px] items-center overflow-hidden rounded-lg border border-brand-100 bg-white">
      <button
        type="button"
        onClick={onDecrease}
        className="flex size-7 items-center justify-center text-stone-500 transition hover:bg-stone-50 hover:text-brand-700"
        aria-label="Diminuir quantidade"
      >
        <Minus className="size-3.5" strokeWidth={2.2} />
      </button>
      <label className="relative min-w-0 border-x border-brand-100">
        <input
          type="number"
          min="0"
          step="0.01"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className="h-7 w-full bg-white px-2 pr-7 text-center text-xs font-black tabular-nums text-stone-900 outline-none"
          placeholder="Qtd"
        />
        <span className="pointer-events-none absolute right-1.5 top-1/2 -translate-y-1/2 text-[9px] font-bold uppercase text-stone-300">
          {unit}
        </span>
      </label>
      <button
        type="button"
        onClick={onIncrease}
        className="flex size-7 items-center justify-center text-brand-700 transition hover:bg-brand-50"
        aria-label="Aumentar quantidade"
      >
        <Plus className="size-3.5" strokeWidth={2.2} />
      </button>
    </div>
  )
}

function IngredientList({
  title,
  subtitle,
  search,
  onSearchChange,
  variant = 'available',
  children,
}: {
  title: string
  subtitle: string
  search?: string
  onSearchChange?: (value: string) => void
  variant?: 'available' | 'cart'
  children: ReactNode
}) {
  const compact = variant === 'cart'

  return (
    <section
      className={[
        'overflow-hidden rounded-xl border shadow-sm',
        compact
          ? 'border-stone-200 bg-white'
          : 'border-stone-200 bg-white',
      ].join(' ')}
    >
      <div
        className={[
          'border-b',
          compact ? 'border-stone-100 px-4 py-3' : 'border-stone-100 p-5',
        ].join(' ')}
      >
        <h2
          className={[
            'font-black text-stone-900',
            compact ? 'text-sm' : 'text-base',
          ].join(' ')}
        >
          {title}
        </h2>
        <p className={compact ? 'mt-0.5 text-[11px] text-stone-500' : 'mt-1 text-xs text-stone-400'}>
          {subtitle}
        </p>
        {onSearchChange && (
          <div className="relative mt-4">
            <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-stone-400" />
            <input
              value={search}
              onChange={(event) => onSearchChange(event.target.value)}
              className={`${inputClass} pl-9`}
              placeholder="Buscar ingrediente"
            />
          </div>
        )}
      </div>
      <div className={compact ? 'max-h-[430px] overflow-auto' : 'max-h-[560px] overflow-auto'}>
        {children}
      </div>
    </section>
  )
}

function PedidosTable({
  pedidos,
  isLoading = false,
  isError = false,
  emptyMessage = 'Nenhum pedido encontrado.',
  showExpectedDate = true,
  pagination,
  onMarkDelivered,
  deliveringGroupKey,
}: {
  pedidos: PedidoGroup[]
  isLoading?: boolean
  isError?: boolean
  emptyMessage?: string
  showExpectedDate?: boolean
  pagination?: React.ComponentProps<typeof DataTable>['pagination']
  onMarkDelivered?: (pedido: PedidoGroup) => void
  deliveringGroupKey?: string
}) {
  const headers = showExpectedDate ? pedidoHeaders : pedidoHeadersWithoutExpected
  const rowOffset = pagination ? (pagination.page - 1) * pagination.pageSize : 0

  return (
    <DataTable
      headers={headers}
      colSpan={headers.length}
      minWidth={showExpectedDate ? '1120px' : '980px'}
      isEmpty={isError || pedidos.length === 0}
      isLoading={isLoading}
      emptyMessage={isError ? 'Nao foi possivel carregar os pedidos.' : emptyMessage}
      loadingMessage="Carregando pedidos..."
      pagination={pagination}
      embedded
    >
      {pedidos.map((pedido, index) => {
        const displayId = `PED-${String(rowOffset + index + 1).padStart(4, '0')}`
        const deliveryDue = showExpectedDate && isDeliveryDue(pedido.expected_date)
        const groupKey = `${pedido.supplier_id}-${pedido.order_date}`
        const isDelivering = deliveringGroupKey === groupKey
        return (
        <tr
          key={pedido.group_key}
          className={[
            'border-b border-stone-100 transition-colors last:border-0 hover:bg-stone-50',
            deliveryDue ? 'saltim-alert' : '',
          ].join(' ')}
        >
          <BodyCell strong>
            <Link
              to="/pedidos/grupos/$supplierId/$orderDate"
              params={{ supplierId: pedido.supplier_id, orderDate: pedido.order_date }}
              className="text-stone-900 transition hover:text-brand-600 hover:underline"
            >
              {displayId}
            </Link>
          </BodyCell>
          <BodyCell>{fmt.date(pedido.order_date)}</BodyCell>
          <BodyCell strong>{pedido.supplier_name}</BodyCell>
          <BodyCell align="right">{fmt.number(pedido.ingredients_count, 0)}</BodyCell>
          <BodyCell align="right">{fmt.number(pedido.items_qty, 2)}</BodyCell>
          <BodyCell align="right">{fmt.currency(pedido.total_value)}</BodyCell>
          <BodyCell align="center">
            <StatusPill status={pedido.status} />
          </BodyCell>
          {showExpectedDate && (
            <BodyCell>
              <div className="flex flex-wrap items-center gap-2">
                <span className="inline-flex items-center gap-1.5 text-stone-700">
                  <CalendarDays className="size-4 text-brand-600" strokeWidth={1.9} />
                  {fmt.date(pedido.expected_date)}
                </span>
                {onMarkDelivered && (
                  <button
                    type="button"
                    onClick={() => onMarkDelivered(pedido)}
                    disabled={isDelivering}
                    className={[
                      'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-black transition disabled:cursor-not-allowed disabled:opacity-60',
                      deliveryDue
                        ? 'saltim-alert-soft hover:border-brand-300 hover:bg-brand-50'
                        : 'border-stone-200 bg-white text-brand-700 hover:bg-brand-50',
                    ].join(' ')}
                  >
                    {deliveryDue ? (
                      <AlertTriangle className="size-3" strokeWidth={2} />
                    ) : (
                      <Check className="size-3" strokeWidth={2} />
                    )}
                    {isDelivering ? 'Atualizando...' : 'Marcar entrega'}
                  </button>
                )}
              </div>
            </BodyCell>
          )}
        </tr>
        )
      })}
    </DataTable>
  )
}

function BodyCell({
  children,
  align = 'left',
  strong = false,
}: {
  children: ReactNode
  align?: 'left' | 'right' | 'center'
  strong?: boolean
}) {
  return (
    <td
      className={[
        'px-4 py-3 text-stone-600',
        align === 'right' ? 'text-right' : align === 'center' ? 'text-center' : 'text-left',
        strong ? 'font-medium text-stone-900' : '',
      ].join(' ')}
    >
      {children}
    </td>
  )
}

function StatusPill({ status }: { status: string }) {
  const delivered = status.toLowerCase() === 'entregue'
  return (
    <span
      className={[
        'inline-flex rounded-full border px-2.5 py-1 text-xs font-bold capitalize',
        delivered
          ? 'saltim-success-soft'
          : 'saltim-alert-soft',
      ].join(' ')}
    >
      {formatStatus(status)}
    </span>
  )
}

function MetricPill({ label, value }: { label: string; value: string }) {
  return (
    <span className="rounded-full border border-stone-200 bg-stone-50 px-2.5 py-1 font-semibold text-stone-600">
      {label}: {value}
    </span>
  )
}

function EmptyState({ children }: { children: ReactNode }) {
  return <div className="px-4 py-16 text-center text-sm text-stone-400">{children}</div>
}

function EmptyPanel({ children }: { children: ReactNode }) {
  return (
    <section className="rounded-xl border border-stone-200 bg-white p-10 text-center text-sm text-stone-400 shadow-sm">
      {children}
    </section>
  )
}

function buildReviewGroups(
  items: PedidoRecommendationItem[],
  supplierByIngredient: Record<string, string>,
) {
  const groups = new Map<
    string,
    {
      supplierId: string
      supplierName: string
      expectedDate: string
      totalValue: number
      items: Array<{ ingredientName: string; qty: number; unit: string }>
    }
  >()

  items.forEach((item) => {
    const supplierId = supplierByIngredient[item.ingredient_id]
    const option = item.options.find((candidate) => candidate.supplier_id === supplierId)
    if (!option) return

    const group = groups.get(supplierId) ?? {
      supplierId,
      supplierName: option.supplier_name,
      expectedDate: option.expected_date,
      totalValue: 0,
      items: [],
    }
    if (new Date(`${option.expected_date}T00:00:00`) > new Date(`${group.expectedDate}T00:00:00`)) {
      group.expectedDate = option.expected_date
    }
    group.totalValue += option.total_value
    group.items.push({
      ingredientName: item.ingredient_name,
      qty: item.qty,
      unit: item.unit,
    })
    groups.set(supplierId, group)
  })

  return Array.from(groups.values()).sort((a, b) =>
    a.supplierName.localeCompare(b.supplierName),
  )
}

function formatEmailNotice(results: PedidoEmailResult[]) {
  const disabled = results.filter((result) => result.status === 'disabled')
  const missing = results.filter((result) => result.status === 'missing_email')
  const failed = results.filter((result) => result.status === 'failed')
  const parts: string[] = []

  if (disabled.length > 0) {
    parts.push('SMTP nao configurado; nenhum email foi enviado.')
  }
  if (missing.length > 0) {
    parts.push(
      `Sem email cadastrado: ${missing.map((result) => result.supplier_name).join(', ')}.`,
    )
  }
  if (failed.length > 0) {
    parts.push(
      `Falha no envio: ${failed.map((result) => result.supplier_name).join(', ')}.`,
    )
  }

  return `Pedido criado. ${parts.join(' ')}`
}

function formatStatus(status: string) {
  const normalized = status.toLowerCase().replace(/_/g, ' ')
  if (normalized === 'em transito') return 'Em trânsito'
  return normalized.charAt(0).toUpperCase() + normalized.slice(1)
}

const inputClass =
  'h-9 w-full rounded-lg border border-stone-200 bg-white px-3 text-sm text-stone-700 outline-none transition focus:border-brand-600 focus:ring-2 focus:ring-brand-600/20'

const pedidoHeaders: DataTableHeader[] = [
  { key: 'id', content: 'Pedido' },
  { key: 'date', content: 'Data' },
  { key: 'supplier', content: 'Fornecedor' },
  { key: 'ingredients', content: 'Ingredientes', align: 'right' },
  { key: 'qty', content: 'Quantidade', align: 'right' },
  { key: 'value', content: 'Valor total', align: 'right' },
  { key: 'status', content: 'Status', align: 'center' },
  { key: 'expected', content: 'Previsão' },
]

const pedidoHeadersWithoutExpected = pedidoHeaders.filter(
  (header) => header.key !== 'expected',
)

const pedidoItemHeaders: DataTableHeader[] = [
  { key: 'ingredient', content: 'Ingrediente' },
  { key: 'category', content: 'Categoria' },
  { key: 'unit', content: 'Unidade' },
  { key: 'qty', content: 'Qtd', align: 'right' },
  { key: 'unit-price', content: 'Preço unitário', align: 'right' },
  { key: 'total', content: 'Total', align: 'right' },
]

const reviewGroupHeaders: DataTableHeader[] = [
  { key: 'supplier', content: 'Fornecedor' },
  { key: 'items', content: 'Itens' },
  { key: 'expected', content: 'Previsão' },
  { key: 'preview', content: 'Ingredientes' },
  { key: 'total', content: 'Total', align: 'right' },
]
