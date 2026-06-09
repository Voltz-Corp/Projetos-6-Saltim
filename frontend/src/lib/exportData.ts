const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export type ExportArea = 'estoque' | 'pedidos' | 'fornecedores'

export type ExportFormat = 'pdf' | 'excel' | 'csv' | 'json' | 'xml' | 'yaml'
export type DashboardExportFormat = 'pdf' | 'excel'

export const EXPORT_FORMAT_OPTIONS: Array<{ value: ExportFormat; label: string }> = [
  { value: 'pdf', label: 'PDF' },
  { value: 'excel', label: 'Excel' },
  { value: 'csv', label: 'CSV' },
  { value: 'json', label: 'JSON' },
  { value: 'xml', label: 'XML' },
  { value: 'yaml', label: 'YAML' },
]

export interface DownloadExportParams {
  area: ExportArea
  format: ExportFormat
  dateFrom?: string
  dateTo?: string
  themeId?: string
}

export interface DashboardExportFilters {
  days?: number
  allPeriod?: boolean
  categoryIds?: string[]
  eventTypes?: string[]
  years?: string[]
  months?: string[]
  monthKeys?: string[]
  dateFrom?: string
  dateTo?: string
}

export async function downloadExport({
  area,
  format,
  dateFrom,
  dateTo,
  themeId,
}: DownloadExportParams) {
  const params = new URLSearchParams({ format })
  if (themeId) params.set('theme', themeId)
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)

  const response = await fetch(`${API_URL}/api/export/${area}?${params.toString()}`)
  if (!response.ok) {
    const detail = await readErrorDetail(response)
    throw new Error(detail || 'Nao foi possivel exportar os dados.')
  }

  const blob = await response.blob()
  const filename = filenameFromDisposition(response.headers.get('Content-Disposition'))
    ?? fallbackFilename(area, format)
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

export async function downloadDashboardExport(
  format: DashboardExportFormat,
  filters?: DashboardExportFilters,
  themeId?: string,
) {
  const params = new URLSearchParams({ format })
  if (themeId) params.set('theme', themeId)
  appendDashboardFilters(params, filters)

  const response = await fetch(`${API_URL}/api/export/dashboard?${params.toString()}`)
  if (!response.ok) {
    const detail = await readErrorDetail(response)
    throw new Error(detail || 'Nao foi possivel exportar o dashboard.')
  }

  const blob = await response.blob()
  const filename = filenameFromDisposition(response.headers.get('Content-Disposition'))
    ?? `dashboard.${format === 'excel' ? 'xlsx' : 'pdf'}`
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

export async function downloadPurchasePlanExport(
  planId: number,
  format: DashboardExportFormat,
  themeId?: string,
) {
  const params = new URLSearchParams({ format })
  if (themeId) params.set('theme', themeId)

  const response = await fetch(
    `${API_URL}/api/export/compras/planos/${planId}?${params.toString()}`,
  )
  if (!response.ok) {
    const detail = await readErrorDetail(response)
    throw new Error(detail || 'Nao foi possivel exportar o plano de compra.')
  }

  const blob = await response.blob()
  const filename = filenameFromDisposition(response.headers.get('Content-Disposition'))
    ?? `plano_compra_${planId}.${format === 'excel' ? 'xlsx' : 'pdf'}`
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

function appendDashboardFilters(params: URLSearchParams, filters?: DashboardExportFilters) {
  if (!filters) return
  if (filters.days && !filters.allPeriod) params.set('days', String(filters.days))
  if (filters.allPeriod) params.set('all_period', 'true')
  if (filters.dateFrom) params.set('date_from', filters.dateFrom)
  if (filters.dateTo) params.set('date_to', filters.dateTo)
  filters.categoryIds?.forEach(value => params.append('category_ids', value))
  filters.eventTypes?.forEach(value => params.append('event_types', value))
  filters.years?.forEach(value => params.append('years', value))
  filters.months?.forEach(value => params.append('month_numbers', value))
  filters.monthKeys?.forEach(value => params.append('month_keys', value))
}

async function readErrorDetail(response: Response) {
  try {
    const body = await response.json()
    return typeof body?.detail === 'string' ? body.detail : ''
  } catch {
    return ''
  }
}

function filenameFromDisposition(disposition: string | null) {
  const match = disposition?.match(/filename="?([^";]+)"?/i)
  return match?.[1]
}

function fallbackFilename(area: ExportArea, format: ExportFormat) {
  const extension = format === 'excel' ? 'xlsx' : format
  return `${area}.${extension}`
}
