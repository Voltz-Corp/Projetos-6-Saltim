import { useState } from 'react'
import { createRoute, Link, useNavigate } from '@tanstack/react-router'
import {
  ArrowLeft,
  CalendarClock,
  CalendarDays,
  CircleDollarSign,
  Hash,
  PackageCheck,
  Store,
} from 'lucide-react'
import { rootRoute } from './Root'
import { AppSelect } from '../components/AppSelect'
import { DataTable, type DataTableHeader } from '../components/DataTable'
import { KpiCard } from '../components/KpiCard'
import {
  DateFilterControl,
  type DateFilterMode,
} from '../components/DateFilterControl'
import { FilterDrawer, FilterField, FilterSection } from '../components/FilterPanel'
import { useFornecedores } from '../hooks/useFornecedores'
import {
  usePedidoDetail,
  usePedidos,
  usePedidosEmTransito,
  type Pedido,
  type PedidoDetailItem,
  type PedidoFilters,
} from '../hooks/usePedidos'

export const pedidosRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/pedidos',
  component: PedidosPage,
})

export const pedidoDetailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/pedidos/$id',
  component: PedidoDetailPage,
})

type OrdersView = 'history' | 'transit'

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

  return (
    <div className="flex h-screen flex-col bg-surface">
      <header className="flex flex-shrink-0 items-center justify-between border-b border-stone-200 bg-white px-8 py-5">
        <div>
          <h1 className="text-xl font-semibold text-stone-900">Pedidos</h1>
          <p className="mt-1 text-xs tabular-nums text-stone-400">
            {isFetching || isFetchingTransit
              ? 'Carregando...'
              : `${activeTotal} pedidos encontrados`}
          </p>
        </div>
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
          <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
            <SegmentedToggle value={view} onChange={setView} />
          </div>
        </section>

        <DataPanel
          title={view === 'history' ? 'Histórico de pedidos' : 'Pedidos em trânsito'}
          subtitle={
            view === 'history'
              ? 'Todos os pedidos registrados'
              : 'Pedidos que ainda têm entrega prevista'
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
            />
          )}
        </DataPanel>
      </main>
    </div>
  )
}

function PedidoDetailPage() {
  const navigate = useNavigate()
  const { id } = pedidoDetailRoute.useParams()
  const { data, isFetching, isError } = usePedidoDetail(id)

  return (
    <div className="flex h-screen flex-col bg-surface">
      <header className="flex flex-shrink-0 items-center gap-3 border-b border-stone-200 bg-white px-8 py-4">
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
            Detalhe do pedido
          </p>
          <h1 className="truncate text-xl font-semibold text-stone-900">
            {id}
          </h1>
        </div>
      </header>

      <main className="flex-1 space-y-6 overflow-auto p-6">
        {isFetching ? (
          <section className="rounded-xl border border-stone-200 bg-white p-10 text-center text-sm text-stone-400 shadow-sm">
            Carregando pedido...
          </section>
        ) : isError || !data ? (
          <section className="rounded-xl border border-stone-200 bg-white p-10 text-center text-sm text-stone-400 shadow-sm">
            Pedido não encontrado.
          </section>
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
                subtitle={`${data.items.length} ingrediente${data.items.length !== 1 ? 's' : ''} no pedido`}
              >
                <PedidoItemsTable items={data.items} />
              </DataPanel>

              <aside className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
                <p className="text-sm font-black text-stone-900">Resumo do pedido</p>
                <p className="mt-1 text-xs text-stone-400">
                  Totais calculados pelos itens listados
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


function SummaryMetric({
  icon: Icon,
  label,
  value,
  featured = false,
}: {
  icon: React.ComponentType<{ className?: string; strokeWidth?: number }>
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

const pedidoItemHeaders: DataTableHeader[] = [
  { key: 'ingredient', content: 'Ingrediente' },
  { key: 'category', content: 'Categoria' },
  { key: 'unit', content: 'Unidade' },
  { key: 'qty', content: 'Qtd', align: 'right' },
  { key: 'unit-price', content: 'Preço unitário', align: 'right' },
  { key: 'total', content: 'Total', align: 'right' },
]

function DataPanel({
  title,
  subtitle,
  children,
}: {
  title: string
  subtitle: string
  children: React.ReactNode
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

function PedidosTable({
  pedidos,
  isLoading = false,
  isError = false,
  emptyMessage = 'Nenhum pedido encontrado.',
  showExpectedDate = true,
  pagination,
}: {
  pedidos: Pedido[]
  isLoading?: boolean
  isError?: boolean
  emptyMessage?: string
  showExpectedDate?: boolean
  pagination?: React.ComponentProps<typeof DataTable>['pagination']
}) {
  const headers = showExpectedDate ? pedidoHeaders : pedidoHeadersWithoutExpected

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
      {pedidos.map((pedido) => (
        <tr
          key={pedido.id}
          className="border-b border-stone-100 transition-colors last:border-0 hover:bg-stone-50"
        >
          <BodyCell strong>
            <Link
              to="/pedidos/$id"
              params={{ id: pedido.id }}
              className="text-stone-900 transition hover:text-brand-600 hover:underline"
            >
              {pedido.id}
            </Link>
          </BodyCell>
          <BodyCell>{fmt.date(pedido.order_date)}</BodyCell>
          <BodyCell>{pedido.supplier_name}</BodyCell>
          <BodyCell>{pedido.ingredient_name}</BodyCell>
          <BodyCell align="right">{fmt.number(pedido.items_qty, 2)}</BodyCell>
          <BodyCell align="right">{fmt.currency(pedido.total_value)}</BodyCell>
          <BodyCell align="center">
            <StatusPill status={pedido.status} />
          </BodyCell>
          {showExpectedDate && (
            <BodyCell>
              <span className="inline-flex items-center gap-1.5 text-stone-700">
                <CalendarDays className="size-4 text-brand-600" strokeWidth={1.9} />
                {fmt.date(pedido.expected_date)}
              </span>
            </BodyCell>
          )}
        </tr>
      ))}
    </DataTable>
  )
}

function BodyCell({
  children,
  align = 'left',
  strong = false,
}: {
  children: React.ReactNode
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
          ? 'border-emerald-100 bg-emerald-50 text-emerald-700'
          : 'border-amber-100 bg-amber-50 text-amber-700',
      ].join(' ')}
    >
      {formatStatus(status)}
    </span>
  )
}

function formatStatus(status: string) {
  const normalized = status.toLowerCase().replace(/_/g, ' ')
  if (normalized === 'em transito') return 'Em trânsito'
  return normalized.charAt(0).toUpperCase() + normalized.slice(1)
}

const pedidoHeaders: DataTableHeader[] = [
  { key: 'id', content: 'Pedido' },
  { key: 'date', content: 'Data' },
  { key: 'supplier', content: 'Fornecedor' },
  { key: 'ingredient', content: 'Produto' },
  { key: 'qty', content: 'Quantidade', align: 'right' },
  { key: 'value', content: 'Valor total', align: 'right' },
  { key: 'status', content: 'Status', align: 'center' },
  { key: 'expected', content: 'Previsão' },
]

const pedidoHeadersWithoutExpected = pedidoHeaders.filter(
  (header) => header.key !== 'expected',
)
