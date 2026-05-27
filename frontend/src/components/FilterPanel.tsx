import { useState, type ReactNode } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { Filter, X } from 'lucide-react'

export function FilterPanel({
  children,
  className = '',
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <section
      className={[
        'rounded-xl border border-stone-200 bg-white p-5 shadow-sm',
        className,
      ].join(' ')}
    >
      {children}
    </section>
  )
}

export function FilterDrawer({
  title = 'Filtros',
  subtitle = 'Ajuste os filtros da tela',
  appliedCount = 0,
  open,
  onOpen,
  onClose,
  onApply,
  onClear,
  children,
}: {
  title?: string
  subtitle?: string
  appliedCount?: number
  open: boolean
  onOpen: () => void
  onClose: () => void
  onApply: () => void
  onClear: () => void
  children: ReactNode
}) {
  return (
    <>
      <button
        type="button"
        onClick={open ? onClose : onOpen}
        className="fixed right-0 top-1/2 z-40 flex -translate-y-1/2 items-center gap-2 rounded-l-xl border border-r-0 border-brand-700 bg-brand-600 px-2 py-4 text-xs font-black uppercase tracking-wide text-white transition hover:bg-brand-700"
        aria-label="Abrir filtros"
      >
        <Filter className="size-4" strokeWidth={2} />
        {appliedCount > 0 && (
          <span className="absolute -left-2 -top-2 flex size-5 items-center justify-center rounded-full bg-saltim-red text-[10px] font-black text-white">
            {appliedCount}
          </span>
        )}
      </button>

      {open && (
        <button
          type="button"
          className="fixed inset-0 z-40 bg-saltim-dark/20"
          onClick={onClose}
          aria-label="Fechar filtros"
        />
      )}

      <aside
        className={[
          'fixed right-0 top-0 z-50 h-screen w-[min(92vw,390px)] transform border-l border-stone-200 bg-white transition-transform duration-200',
          open ? 'translate-x-0' : 'translate-x-full',
        ].join(' ')}
      >
        <div className="flex h-[73px] items-center justify-between border-b border-stone-200 px-5">
          <div>
            <h2 className="text-sm font-black text-stone-900">{title}</h2>
            <p className="text-xs text-stone-400">{subtitle}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex size-9 items-center justify-center rounded-lg text-stone-500 transition hover:bg-stone-100 hover:text-stone-900"
            aria-label="Fechar"
          >
            <X className="size-5" strokeWidth={1.9} />
          </button>
        </div>

        <div className="flex h-[calc(100vh-73px)] flex-col overflow-y-auto p-5">
          <div className="space-y-4">{children}</div>

          <div className="mt-auto flex gap-2 border-t border-stone-100 pt-4">
            <button
              type="button"
              onClick={onClear}
              className="flex-1 rounded-lg border border-stone-200 px-3 py-2 text-sm font-bold text-stone-600 transition hover:bg-stone-50"
            >
              Limpar
            </button>
            <button
              type="button"
              onClick={onApply}
              className="flex-1 rounded-lg bg-brand-600 px-3 py-2 text-sm font-bold text-white transition hover:bg-brand-700"
            >
              Aplicar
            </button>
          </div>
        </div>
      </aside>
    </>
  )
}

export function FilterSection({
  title,
  defaultOpen = true,
  children,
}: {
  title: string
  defaultOpen?: boolean
  children: ReactNode
}) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <section className="border-b border-stone-100 py-5 first:pt-0">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-center justify-between text-left"
      >
        <span className="text-xs font-black uppercase tracking-wide text-stone-500">
          {title}
        </span>
        <span className="text-lg font-bold text-brand-600">{open ? '-' : '+'}</span>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            className="overflow-visible"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
          >
            <div className="mt-3 grid gap-3">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  )
}

export function FilterField({
  label,
  children,
}: {
  label: string
  children: ReactNode
}) {
  return (
    <label className="grid gap-1">
      <span className="text-[11px] font-black uppercase tracking-wide text-stone-400">
        {label}
      </span>
      {children}
    </label>
  )
}
