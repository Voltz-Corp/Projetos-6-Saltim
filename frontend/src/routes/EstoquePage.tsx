import { useState } from 'react'
import { createRoute, useNavigate, useSearch, Link } from '@tanstack/react-router'
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  createColumnHelper,
  type SortingState,
} from '@tanstack/react-table'
import { rootRoute } from './Root'
import {
  useEstoquePaginado,
  getStockStatus,
  type StockItem,
  type StockStatusFilter,
} from '../hooks/useEstoque'
import { CATEGORIES, type Category } from '../data/ingredients'
import { StatusBadge } from '../components/StatusBadge'
import { CategoryBadge } from '../components/CategoryBadge'
import { cn } from '../lib/cn'

export const estoqueRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/estoque',
  validateSearch: (s: Record<string, unknown>) => {
    const out: { counted?: string } = {}
    if (typeof s['counted'] === 'string' && s['counted']) out.counted = s['counted']
    return out
  },
  component: EstoquePage,
})

const fmt = {
  currency: (v: number) => v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }),
  qty: (v: number, unit: string) => `${v.toLocaleString('pt-BR', { maximumFractionDigits: 2 })} ${unit}`,
}

const col = createColumnHelper<StockItem>()

const columns = [
  col.accessor('name', {
    header: 'Insumo',
    cell: i => <span className="font-medium text-stone-900">{i.getValue()}</span>,
    enableSorting: true,
  }),
  col.accessor('category', {
    header: 'Categoria',
    cell: i => <CategoryBadge category={i.getValue()} />,
    enableSorting: true,
  }),
  col.accessor('unit', {
    header: 'Un.',
    cell: i => <span className="text-xs text-stone-400 uppercase tracking-wide">{i.getValue()}</span>,
    enableSorting: false,
  }),
  col.accessor('price', {
    header: 'Preço/un',
    cell: i => <span className="tabular-nums text-stone-600">{fmt.currency(i.getValue())}</span>,
    enableSorting: true,
    meta: { align: 'right' },
  }),
  col.accessor('currentQty', {
    header: 'Qtd atual',
    cell: i => (
      <span className="tabular-nums font-medium text-stone-900">
        {fmt.qty(i.getValue(), i.row.original.unit)}
      </span>
    ),
    enableSorting: true,
    meta: { align: 'right' },
  }),
  col.accessor('minQty', {
    header: 'Mínimo',
    cell: i => (
      <span className="tabular-nums text-stone-400">
        {fmt.qty(i.getValue(), i.row.original.unit)}
      </span>
    ),
    enableSorting: true,
    meta: { align: 'right' },
  }),
  col.display({
    id: 'status',
    header: 'Status',
    cell: i => <StatusBadge item={i.row.original} />,
    enableSorting: false,
  }),
  col.display({
    id: 'actions',
    header: '',
    cell: i => (
      <Link
        to="/ingredientes/$id/editar"
        params={{ id: String(i.row.original.id) }}
        className="inline-flex items-center justify-center size-7 rounded-lg text-stone-400 hover:text-stone-700 hover:bg-stone-100 transition-colors"
        title="Editar ingrediente"
      >
        <svg viewBox="0 0 20 20" className="size-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M11 4l4 4-8 8H3v-4l8-8z" />
        </svg>
      </Link>
    ),
    enableSorting: false,
  }),
]

const PAGE_SIZE_OPTIONS = [25, 50, 100]
const STATUS_OPTIONS: StockStatusFilter[] = ['OK', 'Atenção', 'Crítico', 'Esgotado']

const selectClass = 'h-9 px-3 text-sm border border-stone-200 rounded-lg bg-white outline-none focus:ring-2 focus:ring-brand-600/20 focus:border-brand-600 transition text-stone-700 cursor-pointer'

export function EstoquePage() {
  const navigate = useNavigate()
  const { counted } = useSearch({ from: '/estoque' })

  const [sorting, setSorting] = useState<SortingState>([])
  const [category, setCategory] = useState<Category | ''>('')
  const [status, setStatus] = useState<StockStatusFilter | ''>('')
  const [q, setQ] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(50)

  const { data, isFetching } = useEstoquePaginado({
    category: category || undefined,
    status: status || undefined,
    q: q || undefined,
    page,
    pageSize,
  })

  const items = data?.items ?? []
  const total = data?.total ?? 0
  const totalPages = data?.total_pages ?? 1

  const table = useReactTable({
    data: items,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    manualPagination: true,
  })

  function handleFilterChange(fn: () => void) {
    fn()
    setPage(1)
  }

  return (
    <div className="flex flex-col h-screen bg-surface">

      {/* Success banner */}
      {counted && (
        <div className="bg-green-50 border-b border-green-200 px-8 py-3 flex items-center justify-between">
          <span className="text-sm text-green-800 font-medium">
            ✓ Contagem de <strong>{counted}</strong> finalizada e estoque atualizado.
          </span>
          <button
            onClick={() => navigate({ to: '/estoque', search: {}, replace: true })}
            className="text-green-600 hover:text-green-800 text-sm"
          >
            Fechar
          </button>
        </div>
      )}

      {/* Page header */}
      <div className="bg-white border-b border-stone-200 px-8 py-4 flex items-center gap-4 flex-shrink-0">
        <div className="flex-1 min-w-0">
          <h1 className="text-xl font-semibold text-stone-900">Estoque</h1>
          <p className="text-xs text-stone-400 mt-0.5 tabular-nums">
            {isFetching ? 'Carregando…' : `${total} insumos`}
          </p>
        </div>

        {/* Search */}
        <div className="relative">
          <svg viewBox="0 0 20 20" className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-stone-400 pointer-events-none" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="9" cy="9" r="6" /><line x1="13.5" y1="13.5" x2="18" y2="18" />
          </svg>
          <input
            value={q}
            onChange={e => handleFilterChange(() => setQ(e.target.value))}
            placeholder="Buscar insumo…"
            className="pl-9 pr-4 py-2 text-sm border border-stone-200 rounded-lg bg-stone-50 outline-none focus:ring-2 focus:ring-brand-600/20 focus:border-brand-600 w-52 transition"
          />
        </div>

        <button
          onClick={() => navigate({ to: '/estoque/contagem' })}
          className="flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg text-sm font-semibold hover:bg-brand-700 transition-colors flex-shrink-0"
        >
          <svg viewBox="0 0 20 20" className="size-4 flex-shrink-0" fill="currentColor">
            <path d="M6 4l11 6-11 6V4z" />
          </svg>
          Iniciar contagem
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white border-b border-stone-100 px-8 py-3 flex items-center gap-3 flex-shrink-0">
        <span className="text-xs font-medium text-stone-400 uppercase tracking-wide flex-shrink-0">Filtrar por</span>

        <select
          value={category}
          onChange={e => handleFilterChange(() => setCategory(e.target.value as Category | ''))}
          className={selectClass}
        >
          <option value="">Todas as categorias</option>
          {CATEGORIES.map(cat => (
            <option key={cat} value={cat}>{cat}</option>
          ))}
        </select>

        <select
          value={status}
          onChange={e => handleFilterChange(() => setStatus(e.target.value as StockStatusFilter | ''))}
          className={selectClass}
        >
          <option value="">Todos os status</option>
          {STATUS_OPTIONS.map(s => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>

        {(category || status || q) && (
          <button
            onClick={() => { setCategory(''); setStatus(''); setQ(''); setPage(1) }}
            className="text-xs text-stone-400 hover:text-stone-700 transition-colors ml-1"
          >
            Limpar filtros
          </button>
        )}
      </div>

      {/* Table card */}
      <div className="flex-1 overflow-auto p-6">
        <div className="bg-white rounded-xl border border-stone-200 shadow-sm overflow-hidden flex flex-col">

          <div className="overflow-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="bg-stone-50 border-b border-stone-200">
                  {table.getHeaderGroups().flatMap(hg =>
                    hg.headers.map(header => {
                      const align = (header.column.columnDef.meta as { align?: string } | undefined)?.align
                      const sorted = header.column.getIsSorted()
                      return (
                        <th
                          key={header.id}
                          className={cn(
                            'px-4 py-3 text-xs font-semibold text-stone-400 uppercase tracking-wide whitespace-nowrap select-none',
                            align === 'right' ? 'text-right' : 'text-left',
                            header.column.getCanSort() && 'cursor-pointer hover:text-stone-700 transition-colors',
                          )}
                          onClick={header.column.getToggleSortingHandler()}
                        >
                          <span className="inline-flex items-center gap-1">
                            {flexRender(header.column.columnDef.header, header.getContext())}
                            {header.column.getCanSort() && (
                              <span className={cn('transition-opacity', sorted ? 'opacity-100' : 'opacity-40')}>
                                {sorted === 'asc' ? '↑' : sorted === 'desc' ? '↓' : '↕'}
                              </span>
                            )}
                          </span>
                        </th>
                      )
                    })
                  )}
                </tr>
              </thead>
              <tbody>
                {table.getRowModel().rows.length === 0 ? (
                  <tr>
                    <td colSpan={columns.length} className="py-20 text-center text-stone-400 text-sm">
                      {isFetching ? 'Carregando…' : 'Nenhum insumo encontrado.'}
                    </td>
                  </tr>
                ) : (
                  table.getRowModel().rows.map(row => {
                    const s = getStockStatus(row.original)
                    return (
                      <tr
                        key={row.id}
                        className={cn(
                          'border-b border-stone-100 hover:bg-stone-50 transition-colors',
                          s === 'Crítico'  && 'border-l-2 border-l-red-400',
                          s === 'Atenção'  && 'border-l-2 border-l-amber-400',
                          s === 'Esgotado' && 'opacity-60',
                        )}
                      >
                        {row.getVisibleCells().map(cell => {
                          const align = (cell.column.columnDef.meta as { align?: string } | undefined)?.align
                          return (
                            <td
                              key={cell.id}
                              className={cn('px-4 py-3', align === 'right' ? 'text-right' : '')}
                            >
                              {flexRender(cell.column.columnDef.cell, cell.getContext())}
                            </td>
                          )
                        })}
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination — inside the card */}
          <div className="border-t border-stone-100 px-4 py-2.5 flex items-center justify-between flex-shrink-0">
            <div className="flex items-center gap-2">
              <span className="text-xs text-stone-400">Itens por página</span>
              <select
                value={pageSize}
                onChange={e => { setPageSize(Number(e.target.value)); setPage(1) }}
                className="h-7 px-2 text-xs border border-stone-200 rounded-lg bg-white outline-none focus:ring-2 focus:ring-brand-600/20 cursor-pointer"
              >
                {PAGE_SIZE_OPTIONS.map(n => (
                  <option key={n} value={n}>{n}</option>
                ))}
              </select>
            </div>

            <span className="text-xs text-stone-400 tabular-nums">
              {total === 0 ? '0' : `${(page - 1) * pageSize + 1}–${Math.min(page * pageSize, total)}`} de {total}
            </span>

            <div className="flex items-center gap-0.5">
              <PaginationBtn onClick={() => setPage(1)} disabled={page === 1} title="Primeira">«</PaginationBtn>
              <PaginationBtn onClick={() => setPage(p => p - 1)} disabled={page === 1} title="Anterior">‹</PaginationBtn>
              <span className="px-2 py-1 text-xs font-medium text-stone-600 tabular-nums">
                {page} / {totalPages}
              </span>
              <PaginationBtn onClick={() => setPage(p => p + 1)} disabled={page === totalPages} title="Próxima">›</PaginationBtn>
              <PaginationBtn onClick={() => setPage(totalPages)} disabled={page === totalPages} title="Última">»</PaginationBtn>
            </div>
          </div>

        </div>
      </div>
    </div>
  )
}

function PaginationBtn({ onClick, disabled, title, children }: {
  onClick: () => void; disabled: boolean; title: string; children: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={title}
      className="size-7 flex items-center justify-center rounded-lg text-sm text-stone-500 hover:bg-stone-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
    >
      {children}
    </button>
  )
}
