import { useEffect, useRef, useState } from 'react'
import { CalendarDays } from 'lucide-react'
import { DayPicker, type DateRange } from 'react-day-picker'
import 'react-day-picker/style.css'
import { AppSelect } from './AppSelect'

export type DateFilterMode = 'all' | 'day' | 'range' | 'month'

const MODE_OPTIONS = [
  { value: 'all', label: 'Todo o período' },
  { value: 'range', label: 'Período' },
  { value: 'day', label: 'Dia' },
  { value: 'month', label: 'Mês' },
]

const MONTHS = [
  'Jan',
  'Fev',
  'Mar',
  'Abr',
  'Mai',
  'Jun',
  'Jul',
  'Ago',
  'Set',
  'Out',
  'Nov',
  'Dez',
]

export function DateFilterControl({
  mode,
  dateFrom,
  dateTo,
  onChange,
}: {
  mode: DateFilterMode
  dateFrom: string
  dateTo: string
  onChange: (value: { mode: DateFilterMode; dateFrom: string; dateTo: string }) => void
}) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement | null>(null)
  const selectedDay = fromIso(dateFrom)
  const selectedRange = { from: fromIso(dateFrom), to: fromIso(dateTo) }
  const [monthCursor, setMonthCursor] = useState(
    selectedDay ?? new Date(new Date().getFullYear(), new Date().getMonth(), 1),
  )

  useEffect(() => {
    function handleClick(event: MouseEvent) {
      if (!ref.current?.contains(event.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  function updateMode(nextMode: DateFilterMode) {
    onChange({ mode: nextMode, dateFrom: '', dateTo: '' })
    setOpen(nextMode !== 'all')
  }

  return (
    <div className="grid gap-2" ref={ref}>
      <AppSelect
        value={mode}
        onChange={(value) => updateMode(value as DateFilterMode)}
        options={MODE_OPTIONS}
        className="w-full"
      />

      <div className="relative">
        <button
          type="button"
          disabled={mode === 'all'}
          onClick={() => setOpen((value) => !value)}
          className="flex h-9 w-full items-center justify-between rounded-lg border border-stone-200 bg-white px-3 text-left text-sm text-stone-700 outline-none transition hover:border-stone-300 disabled:cursor-not-allowed disabled:bg-stone-50 disabled:text-stone-400"
        >
          <span>{labelFor(mode, dateFrom, dateTo)}</span>
          <CalendarDays className="size-4 text-brand-600" strokeWidth={1.9} />
        </button>

        {open && mode !== 'all' && (
          <div className="absolute right-0 top-11 z-[80] rounded-xl border border-stone-200 bg-white p-3">
            {mode === 'range' && (
              <DayPicker
                mode="range"
                selected={selectedRange}
                onSelect={(range?: DateRange) => {
                  onChange({
                    mode,
                    dateFrom: toIso(range?.from),
                    dateTo: toIso(range?.to),
                  })
                  if (range?.from && range.to) setOpen(false)
                }}
                numberOfMonths={1}
                captionLayout="dropdown"
                className="saltim-day-picker"
              />
            )}

            {mode === 'day' && (
              <DayPicker
                mode="single"
                selected={selectedDay}
                onSelect={(day?: Date) => {
                  const iso = toIso(day)
                  onChange({ mode, dateFrom: iso, dateTo: iso })
                  if (day) setOpen(false)
                }}
                captionLayout="dropdown"
                className="saltim-day-picker"
              />
            )}

            {mode === 'month' && (
              <div className="w-72">
                <div className="mb-3 flex items-center justify-between">
                  <button
                    type="button"
                    onClick={() =>
                      setMonthCursor((date) =>
                        new Date(date.getFullYear() - 1, date.getMonth(), 1),
                      )
                    }
                    className="rounded-lg px-2 py-1 text-sm font-bold text-stone-500 hover:bg-stone-100"
                  >
                    ‹
                  </button>
                  <span className="text-sm font-black text-stone-900">
                    {monthCursor.getFullYear()}
                  </span>
                  <button
                    type="button"
                    onClick={() =>
                      setMonthCursor((date) =>
                        new Date(date.getFullYear() + 1, date.getMonth(), 1),
                      )
                    }
                    className="rounded-lg px-2 py-1 text-sm font-bold text-stone-500 hover:bg-stone-100"
                  >
                    ›
                  </button>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  {MONTHS.map((month, index) => (
                    <button
                      key={month}
                      type="button"
                      onClick={() => {
                        const first = new Date(monthCursor.getFullYear(), index, 1)
                        const last = new Date(monthCursor.getFullYear(), index + 1, 0)
                        onChange({
                          mode,
                          dateFrom: toIso(first),
                          dateTo: toIso(last),
                        })
                        setOpen(false)
                      }}
                      className="rounded-lg px-3 py-2 text-sm font-bold text-stone-600 hover:bg-brand-50 hover:text-brand-700"
                    >
                      {month}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function labelFor(mode: DateFilterMode, dateFrom: string, dateTo: string) {
  if (mode === 'all') return 'Todas as datas'
  if (mode === 'day') return dateFrom ? formatDate(dateFrom) : 'Selecionar dia'
  if (mode === 'month') {
    if (!dateFrom) return 'Selecionar mês'
    return new Date(`${dateFrom}T00:00:00`).toLocaleDateString('pt-BR', {
      month: 'long',
      year: 'numeric',
    })
  }
  if (dateFrom && dateTo) return `${formatDate(dateFrom)} - ${formatDate(dateTo)}`
  if (dateFrom) return `${formatDate(dateFrom)} - ...`
  return 'Selecionar período'
}

function formatDate(value: string) {
  return new Date(`${value}T00:00:00`).toLocaleDateString('pt-BR')
}

function fromIso(value: string) {
  if (!value) return undefined
  return new Date(`${value}T00:00:00`)
}

function toIso(value?: Date) {
  if (!value) return ''
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}
