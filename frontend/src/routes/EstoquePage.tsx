import { useState, useMemo } from 'react'
import { createRoute, useNavigate, useSearch } from '@tanstack/react-router'
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  createColumnHelper,
  type SortingState,
} from '@tanstack/react-table'
import { rootRoute } from './Root'
import { useEstoque, getStockStatus, type StockItem } from '../hooks/useEstoque'
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
]

export function EstoquePage() {
  const navigate = useNavigate()
  const { counted } = useSearch({ from: '/estoque' })
  const { data: stock = [] } = useEstoque()

  const [sorting, setSorting] = useState<SortingState>([])
  const [selectedCategory, setSelectedCategory] = useState<Category | null>(null)
  const [search, setSearch] = useState('')

  const filtered = useMemo(() => {
    let r = stock
    if (selectedCategory) r = r.filter(i => i.category === selectedCategory)
    if (search) r = r.filter(i => i.name.toLowerCase().includes(search.toLowerCase()))
    return r
  }, [stock, selectedCategory, search])

  const table = useReactTable({
    data: filtered,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  })

  const criticalCount = stock.filter(i => getStockStatus(i) === 'Crítico').length

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
          <p className="text-xs text-stone-400 mt-0.5">
            {filtered.length === stock.length
              ? `${stock.length} insumos`
              : `${filtered.length} de ${stock.length} insumos`}
          </p>
        </div>

        {/* Search */}
        <div className="relative">
          <svg viewBox="0 0 20 20" className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-stone-400 pointer-events-none" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="9" cy="9" r="6" /><line x1="13.5" y1="13.5" x2="18" y2="18" />
          </svg>
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Buscar insumo…"
            className="pl-9 pr-4 py-2 text-sm border border-stone-200 rounded-lg bg-stone-50 outline-none focus:ring-2 focus:ring-brand-600/20 focus:border-brand-600 w-56 transition"
          />
        </div>

        {/* Iniciar contagem — no topo, como manda o figurino */}
        <button
          onClick={() => navigate({ to: '/contagem' })}
          className="flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg text-sm font-semibold hover:bg-brand-700 transition-colors flex-shrink-0"
        >
          <svg viewBox="0 0 20 20" className="size-4" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="9 11 12 14 20 6" /><path d="M20 12v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6a2 2 0 012-2h9" />
          </svg>
          Iniciar contagem
          {criticalCount > 0 && (
            <span className="bg-white/25 text-white text-xs font-semibold px-1.5 py-0.5 rounded-md">
              {criticalCount}
            </span>
          )}
        </button>
      </div>

      {/* Category chips */}
      <div className="bg-white border-b border-stone-100 px-8 py-2.5 flex gap-2 flex-wrap flex-shrink-0">
        <CategoryChip active={!selectedCategory} onClick={() => setSelectedCategory(null)}>
          Todos
        </CategoryChip>
        {CATEGORIES.map(cat => (
          <CategoryChip
            key={cat}
            active={selectedCategory === cat}
            onClick={() => setSelectedCategory(selectedCategory === cat ? null : cat)}
          >
            {cat}
          </CategoryChip>
        ))}
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto">
        <table className="w-full text-sm border-collapse">
          <thead className="sticky top-0 z-10">
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
                          <span className={cn('transition-opacity', sorted ? 'opacity-100' : 'opacity-0 group-hover:opacity-40')}>
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
          <tbody className="bg-white">
            {table.getRowModel().rows.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="py-20 text-center text-stone-400 text-sm">
                  Nenhum insumo encontrado para "{search}"
                </td>
              </tr>
            ) : (
              table.getRowModel().rows.map(row => {
                const status = getStockStatus(row.original)
                return (
                  <tr
                    key={row.id}
                    className={cn(
                      'border-b border-stone-100 hover:bg-stone-50 transition-colors',
                      status === 'Crítico'  && 'border-l-2 border-l-red-400',
                      status === 'Atenção'  && 'border-l-2 border-l-amber-400',
                      status === 'Esgotado' && 'opacity-60',
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
    </div>
  )
}

function CategoryChip({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'px-3 py-1 rounded-full text-xs font-medium transition-colors whitespace-nowrap',
        active
          ? 'bg-stone-900 text-white'
          : 'bg-stone-100 text-stone-600 hover:bg-stone-200',
      )}
    >
      {children}
    </button>
  )
}
