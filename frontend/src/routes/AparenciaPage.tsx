import { createRoute } from '@tanstack/react-router'
import { Check, Moon, Palette, Sun } from 'lucide-react'
import { rootRoute } from './Root'
import { THEME_OPTIONS, useAppearance, type AppearanceMode, type ThemeOption } from '../theme/appearance'

export const aparenciaRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/configuracoes/aparencia',
  component: AparenciaPage,
})

export const aparenciaAliasRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/aparencia',
  component: AparenciaPage,
})

function AparenciaPage() {
  const { themeId, mode, setMode, setThemeId } = useAppearance()

  return (
    <div className="flex h-screen flex-col bg-surface">
      <header className="flex h-[73px] flex-shrink-0 items-center justify-between gap-4 border-b border-stone-200 bg-white px-8">
        <div>
          <p className="text-xs font-bold uppercase tracking-wide text-brand-600">
            Configuracoes
          </p>
          <h1 className="text-xl font-semibold text-stone-900">
            Aparencia
          </h1>
        </div>
        <div className="hidden items-center gap-2 rounded-lg border border-stone-200 bg-stone-50 px-3 py-2 text-xs font-bold text-stone-600 sm:flex">
          <Palette className="size-4 text-brand-600" strokeWidth={2} />
          Aplicacao global e persistente
        </div>
      </header>

      <main className="flex-1 overflow-auto p-6">
        <div className="mx-auto flex max-w-6xl flex-col gap-6">
          <section className="rounded-lg border border-stone-200 bg-white p-5">
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div>
                <h2 className="text-base font-black text-stone-900">Modo</h2>
                <p className="mt-1 text-sm font-medium text-stone-500">
                  Alterne rapidamente entre a base clara e escura do Saltim.
                </p>
              </div>
              <div className="grid w-full max-w-sm grid-cols-2 rounded-lg border border-stone-200 bg-stone-50 p-1">
                <ModeButton
                  mode="light"
                  active={mode === 'light'}
                  icon={Sun}
                  label="Light"
                  onClick={() => setMode('light')}
                />
                <ModeButton
                  mode="dark"
                  active={mode === 'dark'}
                  icon={Moon}
                  label="Dark"
                  onClick={() => setMode('dark')}
                />
              </div>
            </div>
          </section>

          <section className="rounded-lg border border-stone-200 bg-white p-5">
            <div className="mb-5 flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
              <div>
                <h2 className="text-base font-black text-stone-900">Temas visuais</h2>
                <p className="mt-1 text-sm font-medium text-stone-500">
                  Escolha uma identidade completa para cores, fundos, cards, tabelas, formularios e menus.
                </p>
              </div>
              <p className="text-xs font-bold uppercase tracking-wide text-stone-400">
                {THEME_OPTIONS.length} opcoes
              </p>
            </div>

            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {THEME_OPTIONS.map((theme) => (
                <ThemeCard
                  key={theme.id}
                  theme={theme}
                  selected={theme.id === themeId}
                  onSelect={() => setThemeId(theme.id)}
                />
              ))}
            </div>
          </section>
        </div>
      </main>
    </div>
  )
}

function ModeButton({
  active,
  icon: Icon,
  label,
  onClick,
}: {
  mode: AppearanceMode
  active: boolean
  icon: typeof Sun
  label: string
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        'inline-flex items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-black transition',
        active
          ? 'bg-white text-brand-700'
          : 'text-stone-500 hover:bg-white hover:text-stone-900',
      ].join(' ')}
    >
      <Icon className="size-4" strokeWidth={2} />
      {label}
    </button>
  )
}

function ThemeCard({
  theme,
  selected,
  onSelect,
}: {
  theme: ThemeOption
  selected: boolean
  onSelect: () => void
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={[
        'group relative overflow-hidden rounded-lg border p-0 text-left transition',
        selected
          ? 'border-brand-600 bg-brand-50'
          : 'border-stone-200 bg-white hover:border-brand-300 hover:bg-stone-50',
      ].join(' ')}
      aria-pressed={selected}
    >
      <ThemePreview theme={theme} />
      <div className="flex items-start justify-between gap-3 p-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="truncate text-sm font-black text-stone-900">{theme.name}</h3>
            <span className="rounded-full bg-stone-100 px-2 py-0.5 text-[10px] font-black uppercase text-stone-500">
              {theme.mode}
            </span>
          </div>
          <p className="mt-1 text-xs font-medium text-stone-500">{theme.description}</p>
        </div>
        {selected && (
          <span className="flex size-7 flex-shrink-0 items-center justify-center rounded-full bg-brand-600 text-white">
            <Check className="size-4" strokeWidth={2.4} />
          </span>
        )}
      </div>
    </button>
  )
}

function ThemePreview({ theme }: { theme: ThemeOption }) {
  return (
    <div
      className="border-b border-stone-200 p-4"
      style={{ background: theme.colors.surface }}
    >
      <div className="flex items-center gap-2">
        <span
          className="size-3 rounded-full"
          style={{ background: theme.colors.primary }}
        />
        <span
          className="size-3 rounded-full"
          style={{ background: theme.colors.secondary }}
        />
        <span
          className="h-2 flex-1 rounded-full"
          style={{ background: theme.colors.card }}
        />
      </div>
      <div
        className="mt-4 rounded-lg p-3"
        style={{ background: theme.colors.card }}
      >
        <div
          className="h-2 w-2/3 rounded-full"
          style={{ background: theme.colors.text, opacity: 0.9 }}
        />
        <div className="mt-2 flex gap-2">
          <div
            className="h-8 flex-1 rounded-md"
            style={{ background: theme.colors.primary }}
          />
          <div
            className="h-8 w-12 rounded-md"
            style={{ background: theme.colors.secondary }}
          />
        </div>
      </div>
    </div>
  )
}
