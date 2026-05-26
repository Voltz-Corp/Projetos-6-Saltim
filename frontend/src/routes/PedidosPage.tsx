import { useState } from 'react'
import { createRoute } from '@tanstack/react-router'
import { CalendarDays, PackageCheck } from 'lucide-react'
import { rootRoute } from './Root'
import { AppSelect } from '../components/AppSelect'
import { DataTable, type DataTableHeader } from '../components/DataTable'
import { useFornecedores } from '../hooks/useFornecedores'
import {
  usePedidos,
  usePedidosEmTransito,
  type Pedido,
  type PedidoFilters,
} from '../hooks/usePedidos'

export const pedidosRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/pedidos',
  component: PedidosPage,
})

const PAGE_SIZE_OPTIONS = [10, 25, 50]
const STATUS_OPTIONS = [
  { value: '', label: 'Todos os status' },
  { value: 'entregue', label: 'Entregue' },
  { value: 'em_transito', label: 'Em trânsito' },
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
  const [status, setStatus] = useState('')
  const [supplierId, setSupplierId] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)

  const filters: PedidoFilters = {
    status: status || undefined,
    supplierId: supplierId || undefined,
    dateFrom: dateFrom || undefined,
    dateTo: dateTo || undefined,
    page,
    pageSize,
  }
  const transitFilters: PedidoFilters = {
    supplierId: supplierId || undefined,
    dateFrom: dateFrom || undefined,
    dateTo: dateTo || undefined,
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

  function resetPage(fn: () => void) {
    fn()
    setPage(1)
  }

  function clearFilters() {
    setStatus('')
    setSupplierId('')
    setDateFrom('')
    setDateTo('')
    setPage(1)
  }

  const items = data?.items ?? []

  return (
    <div className="flex h-screen flex-col bg-surface">
      <header className="flex flex-shrink-0 items-center justify-between border-b border-stone-200 bg-white px-8 py-5">
        <div>
          <h1 className="text-xl font-semibold text-stone-900">Pedidos</h1>
          <p className="mt-1 text-xs tabular-nums text-stone-400">
            {isFetching ? 'Carregando...' : `${data?.total ?? 0} pedidos encontrados`}
          </p>
        </div>
        <div className="hidden size-10 items-center justify-center rounded-xl bg-brand-50 text-brand-600 sm:flex">
          <PackageCheck className="size-5" strokeWidth={2} />
        </div>
      </header>

      <div className="flex flex-shrink-0 flex-wrap items-end gap-3 border-b border-stone-100 bg-white px-8 py-3">
        <FilterField label="Status">
          <AppSelect
            value={status}
            onChange={(value) => resetPage(() => setStatus(value))}
            options={STATUS_OPTIONS}
            className="w-44"
          />
        </FilterField>
        <FilterField label="Fornecedor">
          <AppSelect
            value={supplierId}
            onChange={(value) => resetPage(() => setSupplierId(value))}
            options={supplierOptions}
            className="w-72"
          />
        </FilterField>
        <FilterField label="Início">
          <input
            type="date"
            value={dateFrom}
            onChange={(event) => resetPage(() => setDateFrom(event.target.value))}
            className="h-9 rounded-lg border border-stone-200 bg-white px-3 text-sm text-stone-700 outline-none transition focus:border-brand-600 focus:ring-2 focus:ring-brand-600/20"
          />
        </FilterField>
        <FilterField label="Fim">
          <input
            type="date"
            value={dateTo}
            onChange={(event) => resetPage(() => setDateTo(event.target.value))}
            className="h-9 rounded-lg border border-stone-200 bg-white px-3 text-sm text-stone-700 outline-none transition focus:border-brand-600 focus:ring-2 focus:ring-brand-600/20"
          />
        </FilterField>
        {(status || supplierId || dateFrom || dateTo) && (
          <button
            type="button"
            onClick={clearFilters}
            className="mb-2 text-xs font-bold text-stone-400 transition hover:text-stone-700"
          >
            Limpar filtros
          </button>
        )}
      </div>

      <main className="flex-1 space-y-6 overflow-auto p-6">
        <DataPanel title="Histórico de pedidos" subtitle="Todos os pedidos registrados">
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
        </DataPanel>

        <DataPanel
          title="Pedidos em trânsito"
          subtitle="Pedidos que ainda têm entrega prevista"
        >
          <PedidosTable
            pedidos={inTransit}
            isLoading={isFetchingTransit}
            emptyMessage="Nenhum pedido em trânsito."
            showExpectedDate
          />
        </DataPanel>
      </main>
    </div>
  )
}

function FilterField({
  label,
  children,
}: {
  label: string
  children: React.ReactNode
}) {
  return (
    <label className="grid gap-1">
      <span className="text-[11px] font-black uppercase tracking-wide text-stone-400">
        {label}
      </span>
      {children}
    </label>
  )
}

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
    <section className="overflow-hidden rounded-xl border border-stone-200 bg-white shadow-sm">
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
    >
      {pedidos.map((pedido) => (
        <tr
          key={pedido.id}
          className="border-b border-stone-100 transition-colors last:border-0 hover:bg-stone-50"
        >
          <BodyCell strong>{pedido.id}</BodyCell>
          <BodyCell>{fmt.date(pedido.order_date)}</BodyCell>
          <BodyCell>{pedido.supplier_name}</BodyCell>
          <BodyCell>{pedido.ingredient_name}</BodyCell>
          <BodyCell align="right">{fmt.number(pedido.items_qty, 2)}</BodyCell>
          <BodyCell align="right">{fmt.currency(pedido.total_value)}</BodyCell>
          <BodyCell>
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
  align?: 'left' | 'right'
  strong?: boolean
}) {
  return (
    <td
      className={[
        'px-4 py-3 text-stone-600',
        align === 'right' ? 'text-right' : 'text-left',
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
        'inline-flex rounded-full px-2.5 py-1 text-xs font-bold capitalize',
        delivered
          ? 'bg-emerald-50 text-emerald-700'
          : 'bg-amber-50 text-amber-700',
      ].join(' ')}
    >
      {status.replace('_', ' ')}
    </span>
  )
}

const pedidoHeaders: DataTableHeader[] = [
  { key: 'id', content: 'Pedido' },
  { key: 'date', content: 'Data' },
  { key: 'supplier', content: 'Fornecedor' },
  { key: 'ingredient', content: 'Produto' },
  { key: 'qty', content: 'Qtd itens', align: 'right' },
  { key: 'value', content: 'Valor total', align: 'right' },
  { key: 'status', content: 'Status' },
  { key: 'expected', content: 'Previsão' },
]

const pedidoHeadersWithoutExpected = pedidoHeaders.filter(
  (header) => header.key !== 'expected',
)
