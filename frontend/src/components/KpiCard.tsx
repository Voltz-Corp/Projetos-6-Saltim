import type { LucideIcon } from 'lucide-react'

export type KpiTone = 'orange' | 'blue' | 'green' | 'red' | 'cream'

export interface KpiCardProps {
  icon: LucideIcon
  label: string
  value: string
  detail?: string
  tone?: KpiTone
  truncateValue?: boolean
  showComparisonBadge?: boolean
  comparisonLabel?: string
  comparisonDirection?: 'up' | 'down' | 'neutral'
}

const toneClasses: Record<KpiTone, string> = {
  orange: 'bg-brand-50 text-brand-600',
  blue: 'bg-sky-50 text-saltim-blue',
  green: 'bg-emerald-50 text-saltim-green',
  red: 'bg-red-50 text-saltim-red',
  cream: 'bg-saltim-cream text-stone-900',
}

const badgeClasses = {
  up: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  down: 'border-red-200 bg-red-50 text-red-700',
  neutral: 'border-stone-200 bg-stone-50 text-stone-500',
}

export function KpiCard({
  icon: Icon,
  label,
  value,
  detail,
  tone = 'orange',
  truncateValue = false,
  showComparisonBadge = false,
  comparisonLabel = '',
  comparisonDirection = 'neutral',
}: KpiCardProps) {
  return (
    <section className="relative min-w-0 rounded-xl border border-stone-100 bg-white p-4 shadow-[0_14px_34px_rgba(26,25,24,0.04)]">
      {showComparisonBadge && comparisonLabel && (
        <span
          className={[
            'absolute right-4 top-4 max-w-[44%] truncate rounded-full border px-2 py-1 text-[11px] font-black',
            badgeClasses[comparisonDirection],
          ].join(' ')}
          title={comparisonLabel}
        >
          {comparisonLabel}
        </span>
      )}

      <div className="flex items-start gap-3 pr-1">
        <div
          className={[
            'flex size-9 flex-shrink-0 items-center justify-center rounded-xl',
            toneClasses[tone],
          ].join(' ')}
        >
          <Icon className="size-5" strokeWidth={1.9} />
        </div>

        <div className="min-w-0 flex-1">
          <div className="text-[11px] font-bold uppercase tracking-wide text-stone-500">
            {label}
          </div>
          <div
            className={[
              'mt-1 text-base font-black leading-tight text-stone-900 tabular-nums',
              truncateValue ? 'truncate' : 'break-words',
            ].join(' ')}
            title={truncateValue ? value : undefined}
          >
            {value}
          </div>
          {detail && (
            <div className="mt-1 truncate text-xs leading-snug text-stone-500" title={detail}>
              {detail}
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
