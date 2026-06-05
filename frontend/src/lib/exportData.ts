const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export type ExportArea = 'estoque' | 'pedidos' | 'fornecedores'

export type ExportFormat = 'pdf' | 'excel' | 'csv' | 'json' | 'xml' | 'yaml'

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
}

export async function downloadExport({
  area,
  format,
  dateFrom,
  dateTo,
}: DownloadExportParams) {
  const params = new URLSearchParams({ format })
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
