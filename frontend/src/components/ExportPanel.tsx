import { useMemo, useState } from 'react'
import { Download, FileSpreadsheet } from 'lucide-react'
import { AppSelect } from './AppSelect'
import {
  downloadExport,
  EXPORT_FORMAT_OPTIONS,
  type ExportArea,
  type ExportFormat,
} from '../lib/exportData'
import { useAppearance } from '../theme/appearance'

interface ExportPanelProps {
  area: ExportArea
  title: string
  subtitle: string
  requiresDateRange?: boolean
}

export function ExportPanel({
  area,
  title,
  subtitle,
  requiresDateRange = false,
}: ExportPanelProps) {
  const defaults = useMemo(() => defaultDateRange(), [])
  const { themeId } = useAppearance()
  const [format, setFormat] = useState<ExportFormat>('csv')
  const [dateFrom, setDateFrom] = useState(defaults.dateFrom)
  const [dateTo, setDateTo] = useState(defaults.dateTo)
  const [isExporting, setIsExporting] = useState(false)
  const [error, setError] = useState('')

  async function handleExport() {
    setError('')
    if (requiresDateRange && (!dateFrom || !dateTo)) {
      setError('Informe a data inicial e final para exportar.')
      return
    }
    if (requiresDateRange && dateFrom > dateTo) {
      setError('A data inicial não pode ser maior que a data final.')
      return
    }

    setIsExporting(true)
    try {
      await downloadExport({
        area,
        format,
        dateFrom: requiresDateRange ? dateFrom : undefined,
        dateTo: requiresDateRange ? dateTo : undefined,
        themeId,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Não foi possível exportar.')
    } finally {
      setIsExporting(false)
    }
  }

  return (
    <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="flex min-w-0 gap-3">
          <span className="flex size-10 flex-shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-700">
            <FileSpreadsheet className="size-5" strokeWidth={2} />
          </span>
          <div className="min-w-0">
            <h2 className="text-sm font-black text-stone-900">{title}</h2>
            <p className="mt-1 text-xs font-medium leading-5 text-stone-500">{subtitle}</p>
            {error && <p className="mt-2 text-xs font-bold text-red-600">{error}</p>}
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:flex lg:items-end">
          {requiresDateRange && (
            <>
              <label className="space-y-1">
                <span className="text-[11px] font-bold uppercase tracking-wide text-stone-400">
                  De
                </span>
                <input
                  type="date"
                  value={dateFrom}
                  onChange={(event) => setDateFrom(event.target.value)}
                  className="h-9 rounded-lg border border-stone-200 bg-white px-3 text-sm font-medium text-stone-900 outline-none transition focus:border-brand-600 focus:ring-2 focus:ring-brand-100"
                />
              </label>
              <label className="space-y-1">
                <span className="text-[11px] font-bold uppercase tracking-wide text-stone-400">
                  Ate
                </span>
                <input
                  type="date"
                  value={dateTo}
                  onChange={(event) => setDateTo(event.target.value)}
                  className="h-9 rounded-lg border border-stone-200 bg-white px-3 text-sm font-medium text-stone-900 outline-none transition focus:border-brand-600 focus:ring-2 focus:ring-brand-100"
                />
              </label>
            </>
          )}

          <label className="min-w-36 space-y-1">
            <span className="text-[11px] font-bold uppercase tracking-wide text-stone-400">
              Formato
            </span>
            <AppSelect
              value={format}
              onChange={(value) => setFormat(value as ExportFormat)}
              options={EXPORT_FORMAT_OPTIONS}
              className="min-w-36"
            />
          </label>

          <button
            type="button"
            onClick={handleExport}
            disabled={isExporting}
            className="inline-flex h-9 items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 text-sm font-bold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <Download className="size-4" strokeWidth={2} />
            {isExporting ? 'Exportando...' : 'Exportar'}
          </button>
        </div>
      </div>
    </section>
  )
}

function defaultDateRange() {
  const today = new Date()
  const start = new Date(today)
  start.setDate(today.getDate() - 30)
  return {
    dateFrom: toDateInput(start),
    dateTo: toDateInput(today),
  }
}

function toDateInput(date: Date) {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Recife',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(date)
}
