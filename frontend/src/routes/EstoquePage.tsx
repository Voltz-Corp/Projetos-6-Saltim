import { useState } from 'react';
import {
  createRoute,
  useNavigate,
  useSearch,
  Link,
} from '@tanstack/react-router';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  createColumnHelper,
  type SortingState,
} from '@tanstack/react-table';
import { rootRoute } from './Root';
import {
  useEstoquePaginado,
  getStockStatus,
  type StockItem,
  type StockStatusFilter,
} from '../hooks/useEstoque';
import { CATEGORIES, type Category } from '../data/ingredients';
import { StatusBadge } from '../components/StatusBadge';
import { CategoryBadge } from '../components/CategoryBadge';
import { AppSelect } from '../components/AppSelect';
import { DataTable, type DataTableHeader } from '../components/DataTable';
import {
  FilterDrawer,
  FilterField,
  FilterSection,
} from '../components/FilterPanel';
import { cn } from '../lib/cn';

export const estoqueRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/estoque',
  validateSearch: (s: Record<string, unknown>) => {
    const out: { counted?: string } = {};
    if (typeof s['counted'] === 'string' && s['counted'])
      out.counted = s['counted'];
    return out;
  },
  component: EstoquePage,
});

const fmt = {
  currency: (v: number) =>
    v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }),
  qty: (v: number, unit: string) =>
    `${v.toLocaleString('pt-BR', { maximumFractionDigits: 2 })} ${unit}`,
};

const col = createColumnHelper<StockItem>();

const columns = [
  col.accessor('name', {
    header: 'Insumo',
    cell: (i) => (
      <Link
        to="/estoque/contagem/atual/$index"
        params={{ index: String(CATEGORIES.indexOf(i.row.original.category)) }}
        className="font-medium text-stone-900 hover:text-brand-600 hover:underline transition-colors"
      >
        {i.getValue()}
      </Link>
    ),
    enableSorting: true,
  }),
  col.accessor('category', {
    header: 'Categoria',
    cell: (i) => <CategoryBadge category={i.getValue()} />,
    enableSorting: true,
  }),
  col.accessor('unit', {
    header: 'Un.',
    cell: (i) => (
      <span className="text-xs text-stone-400 uppercase tracking-wide">
        {i.getValue()}
      </span>
    ),
    enableSorting: false,
  }),
  col.accessor('price', {
    header: 'Preço/un',
    cell: (i) => (
      <span className="tabular-nums text-stone-600">
        {fmt.currency(i.getValue())}
      </span>
    ),
    enableSorting: true,
    meta: { align: 'right' },
  }),
  col.accessor('currentQty', {
    header: 'Qtd atual',
    cell: (i) => (
      <span className="tabular-nums font-medium text-stone-900">
        {fmt.qty(i.getValue(), i.row.original.unit)}
      </span>
    ),
    enableSorting: true,
    meta: { align: 'right' },
  }),
  col.accessor('minQty', {
    header: 'Mínimo',
    cell: (i) => (
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
    cell: (i) => <StatusBadge item={i.row.original} />,
    enableSorting: false,
    meta: { align: 'center' },
  }),
  col.display({
    id: 'actions',
    header: '',
    cell: (i) => (
      <Link
        to="/ingredientes/$id/editar"
        params={{ id: String(i.row.original.id) }}
        className="inline-flex items-center justify-center size-7 rounded-lg text-stone-400 hover:text-stone-700 hover:bg-stone-100 transition-colors"
        title="Editar ingrediente"
      >
        <svg
          viewBox="0 0 20 20"
          className="size-4"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M11 4l4 4-8 8H3v-4l8-8z" />
        </svg>
      </Link>
    ),
    enableSorting: false,
  }),
];

const PAGE_SIZE_OPTIONS = [25, 50, 100];
const STATUS_OPTIONS: StockStatusFilter[] = [
  'OK',
  'Crítico',
  'Esgotado',
];

export function EstoquePage() {
  const navigate = useNavigate();
  const { counted } = useSearch({ from: '/estoque' });

  const [sorting, setSorting] = useState<SortingState>([]);
  const [category, setCategory] = useState<Category | ''>('');
  const [status, setStatus] = useState<StockStatusFilter | ''>('');
  const [q, setQ] = useState('');
  const [draftCategory, setDraftCategory] = useState<Category | ''>('');
  const [draftStatus, setDraftStatus] = useState<StockStatusFilter | ''>('');
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);

  const { data, isFetching } = useEstoquePaginado({
    category: category || undefined,
    status: status || undefined,
    q: q || undefined,
    page,
    pageSize,
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = data?.total_pages ?? 1;

  const table = useReactTable({
    data: items,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    manualPagination: true,
  });

  const appliedFilterCount = [category, status].filter(Boolean).length;

  function applyFilters() {
    setCategory(draftCategory);
    setStatus(draftStatus);
    setPage(1);
    setFiltersOpen(false);
  }

  function clearFilters() {
    setCategory('');
    setStatus('');
    setQ('');
    setDraftCategory('');
    setDraftStatus('');
    setPage(1);
    setFiltersOpen(false);
  }

  return (
    <div className="flex flex-col h-screen bg-surface">
      {/* Success banner */}
      {counted && (
        <div className="bg-green-50 border-b border-green-200 px-8 py-3 flex items-center justify-between">
          <span className="text-sm text-green-800 font-medium">
            ✓ Contagem de <strong>{counted}</strong> finalizada e estoque
            atualizado.
          </span>
          <button
            onClick={() =>
              navigate({ to: '/estoque', search: {}, replace: true })
            }
            className="text-green-600 hover:text-green-800 text-sm"
          >
            Fechar
          </button>
        </div>
      )}

      {/* Page header */}
      <div className="flex h-[73px] flex-shrink-0 items-center gap-4 border-b border-stone-200 bg-white px-8">
        <div className="flex-1 min-w-0">
          <h1 className="text-xl font-semibold text-stone-900">Estoque</h1>
          <p className="text-xs text-stone-400 mt-0.5 tabular-nums">
            {isFetching ? 'Carregando…' : `${total} insumos`}
          </p>
        </div>

        <div className="relative">
          <svg
            viewBox="0 0 20 20"
            className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-stone-400 pointer-events-none"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="9" cy="9" r="6" />
            <line x1="13.5" y1="13.5" x2="18" y2="18" />
          </svg>
          <input
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              setPage(1);
            }}
            placeholder="Buscar insumo..."
            className="pl-9 pr-4 py-2 text-sm border border-stone-200 rounded-lg bg-white outline-none focus:border-brand-600 w-52 transition"
          />
        </div>
      </div>

      <FilterDrawer
        title="Filtros de estoque"
        subtitle="Aplicados à listagem de insumos"
        open={filtersOpen}
        onOpen={() => setFiltersOpen(true)}
        onClose={() => setFiltersOpen(false)}
        onApply={applyFilters}
        onClear={clearFilters}
        appliedCount={appliedFilterCount}
      >
        <FilterSection title="Classificação">
          <FilterField label="Categoria">
            <AppSelect
              value={draftCategory}
              onChange={(value) => setDraftCategory(value as Category | '')}
              options={[
                { value: '', label: 'Todas as categorias' },
                ...CATEGORIES.map((cat) => ({ value: cat, label: cat })),
              ]}
              className="w-full"
            />
          </FilterField>

          <FilterField label="Status">
            <AppSelect
              value={draftStatus}
              onChange={(value) =>
                setDraftStatus(value as StockStatusFilter | '')
              }
              options={[
                { value: '', label: 'Todos os status' },
                ...STATUS_OPTIONS.map((s) => ({ value: s, label: s })),
              ]}
              className="w-full"
            />
          </FilterField>
        </FilterSection>
      </FilterDrawer>

      {/* Table card */}
      <div className="flex-1 overflow-auto p-6">
        <DataTable
          headers={stockHeaders(table)}
          colSpan={columns.length}
          minWidth="920px"
          isEmpty={table.getRowModel().rows.length === 0}
          isLoading={isFetching}
          emptyMessage="Nenhum insumo encontrado."
          loadingMessage="Carregando..."
          pagination={{
            page,
            pageSize,
            total,
            totalPages,
            pageSizeOptions: PAGE_SIZE_OPTIONS,
            onPageChange: setPage,
            onPageSizeChange: (value) => {
              setPageSize(value);
              setPage(1);
            },
          }}
        >
          {table.getRowModel().rows.map((row) => {
            const s = getStockStatus(row.original);
            return (
              <tr
                key={row.id}
                className={cn(
                  'border-b border-stone-100 hover:bg-stone-50 transition-colors',
                  s === 'Crítico' && 'border-l-2 border-l-red-400',
                  s === 'Esgotado' && 'opacity-60',
                )}
              >
                {row.getVisibleCells().map((cell) => {
                  const align = (
                    cell.column.columnDef.meta as { align?: string } | undefined
                  )?.align;
                  return (
                    <td
                      key={cell.id}
                      className={cn(
                        'px-4 py-3',
                        align === 'right' ? 'text-right' : '',
                      )}
                    >
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext(),
                      )}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </DataTable>
      </div>
    </div>
  );
}

function stockHeaders(
  table: ReturnType<typeof useReactTable<StockItem>>,
): DataTableHeader[] {
  return table.getHeaderGroups().flatMap((hg) =>
    hg.headers.map((header) => {
      const align = (
        header.column.columnDef.meta as { align?: string } | undefined
      )?.align;
      const sorted = header.column.getIsSorted();
      const canSort = header.column.getCanSort();

      return {
        key: header.id,
        align: align === 'right' ? 'right' : 'left',
        onClick: canSort ? () => header.column.toggleSorting() : undefined,
        content: (
          <span className="inline-flex items-center gap-1">
            {flexRender(header.column.columnDef.header, header.getContext())}
            {canSort && (
              <span
                className={cn(
                  'transition-opacity',
                  sorted ? 'opacity-100' : 'opacity-40',
                )}
              >
                {sorted === 'asc' ? '↑' : sorted === 'desc' ? '↓' : '↕'}
              </span>
            )}
          </span>
        ),
      };
    }),
  );
}
