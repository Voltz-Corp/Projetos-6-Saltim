import type { ReactNode } from 'react'
import { AppSelect } from './AppSelect'
import { cn } from '../lib/cn'

export interface DataTableHeader {
  key: string
  content: ReactNode
  align?: 'left' | 'right' | 'center'
  className?: string
  onClick?: () => void
}

export interface DataTablePagination {
  page: number
  pageSize: number
  total: number
  totalPages: number
  onPageChange: (page: number) => void
  onPageSizeChange?: (pageSize: number) => void
  pageSizeOptions?: number[]
}

export function DataTable({
  headers,
  children,
  colSpan,
  minWidth,
  emptyMessage = 'Nenhum item encontrado.',
  loadingMessage = 'Carregando...',
  isEmpty = false,
  isLoading = false,
  pagination,
  embedded = false,
}: {
  headers: DataTableHeader[]
  children: ReactNode
  colSpan?: number
  minWidth?: string
  emptyMessage?: string
  loadingMessage?: string
  isEmpty?: boolean
  isLoading?: boolean
  pagination?: DataTablePagination
  embedded?: boolean
}) {
  const span = colSpan ?? headers.length

  return (
    <div
      className={cn(
        'overflow-hidden bg-white',
        embedded ? 'rounded-none border-0' : 'rounded-xl border border-stone-200',
      )}
    >
      <div className="overflow-auto">
        <table className="w-full border-collapse text-sm" style={{ minWidth }}>
          <thead>
            <tr className="border-b border-stone-200 bg-stone-50">
              {headers.map((header) => (
                <th
                  key={header.key}
                  onClick={header.onClick}
                  className={cn(
                    'whitespace-nowrap px-4 py-3 text-xs font-semibold uppercase tracking-wide text-stone-400 select-none',
                    header.align === 'right' ? 'text-right' : '',
                    header.align === 'center' ? 'text-center' : '',
                    !header.align || header.align === 'left' ? 'text-left' : '',
                    header.onClick && 'cursor-pointer transition-colors hover:text-stone-700',
                    header.className,
                  )}
                >
                  {header.content}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {isEmpty ? (
              <tr>
                <td colSpan={span} className="py-20 text-center text-sm text-stone-400">
                  {isLoading ? loadingMessage : emptyMessage}
                </td>
              </tr>
            ) : (
              children
            )}
          </tbody>
        </table>
      </div>

      {pagination && (
        <div className="flex flex-shrink-0 items-center justify-between border-t border-stone-100 px-4 py-2.5">
          <div className="flex items-center gap-2">
            {pagination.onPageSizeChange && (
              <>
                <span className="text-xs text-stone-400">Itens por página</span>
                <AppSelect
                  value={String(pagination.pageSize)}
                  onChange={(value) => pagination.onPageSizeChange?.(Number(value))}
                  options={(pagination.pageSizeOptions ?? [10, 25, 50]).map((value) => ({
                    value: String(value),
                    label: String(value),
                  }))}
                  className="w-20"
                />
              </>
            )}
          </div>

          <span className="text-xs tabular-nums text-stone-400">
            {pagination.total === 0
              ? '0'
              : `${(pagination.page - 1) * pagination.pageSize + 1}-${Math.min(
                  pagination.page * pagination.pageSize,
                  pagination.total,
                )}`}{' '}
            de {pagination.total}
          </span>

          <div className="flex items-center gap-0.5">
            <PaginationButton
              onClick={() => pagination.onPageChange(1)}
              disabled={pagination.page === 1}
              title="Primeira"
            >
              «
            </PaginationButton>
            <PaginationButton
              onClick={() => pagination.onPageChange(pagination.page - 1)}
              disabled={pagination.page === 1}
              title="Anterior"
            >
              ‹
            </PaginationButton>
            <span className="px-2 py-1 text-xs font-medium tabular-nums text-stone-600">
              {pagination.page} / {pagination.totalPages}
            </span>
            <PaginationButton
              onClick={() => pagination.onPageChange(pagination.page + 1)}
              disabled={pagination.page === pagination.totalPages}
              title="Próxima"
            >
              ›
            </PaginationButton>
            <PaginationButton
              onClick={() => pagination.onPageChange(pagination.totalPages)}
              disabled={pagination.page === pagination.totalPages}
              title="Última"
            >
              »
            </PaginationButton>
          </div>
        </div>
      )}
    </div>
  )
}

function PaginationButton({
  onClick,
  disabled,
  title,
  children,
}: {
  onClick: () => void
  disabled: boolean
  title: string
  children: ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={title}
      className="flex size-7 items-center justify-center rounded-lg text-sm text-stone-500 transition-colors hover:bg-stone-100 disabled:cursor-not-allowed disabled:opacity-30"
    >
      {children}
    </button>
  )
}
