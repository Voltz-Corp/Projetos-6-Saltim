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
  badgeValue?: boolean
  badgeTone?: 'green' | 'amber' | 'red'
}

const toneClasses: Record<KpiTone, string> = {
  orange: 'bg-brand-50 text-brand-600',
  blue: 'saltim-info-soft',
  green: 'saltim-success-soft',
  red: 'saltim-danger-soft',
  cream: 'bg-saltim-cream text-stone-900',
}

const badgeClasses = {
  up: 'saltim-success-soft',
  down: 'saltim-danger-soft',
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
  badgeValue = false,
  badgeTone = 'green',
}: KpiCardProps) {
  const valueBadgeClasses = {
    green: 'saltim-success-soft',
    amber: 'saltim-alert-soft',
    red: 'saltim-danger-soft',
  }

  return (
    <section className="relative min-w-0 rounded-xl border border-stone-200 bg-white p-4">
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
          {badgeValue ? (
            <span className={`mt-1 inline-flex rounded-full border px-2.5 py-1 text-xs font-black capitalize ${valueBadgeClasses[badgeTone]}`}>
              {value}
            </span>
          ) : (
            <div
              className={[
                'mt-1 text-base font-black leading-tight text-stone-900 tabular-nums',
                truncateValue ? 'truncate' : 'break-words',
              ].join(' ')}
              title={truncateValue ? value : undefined}
            >
              {value}
            </div>
          )}
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
