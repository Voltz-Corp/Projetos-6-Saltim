import { useEffect, useMemo, useState, type CSSProperties } from 'react'
import { createRoute } from '@tanstack/react-router'
import { Check, Moon, Palette, Search, Sun, Trophy } from 'lucide-react'
import { rootRoute } from './Root'
import {
  CLASSIC_THEME_OPTIONS,
  WORLD_CUP_THEME_OPTIONS,
  useAppearance,
  type AppearanceMode,
  type ThemeOption,
} from '../theme/appearance'

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
  const initialCollection = WORLD_CUP_THEME_OPTIONS.some((theme) => theme.id === themeId)
    ? 'world-cup'
    : 'classic'
  const [collection, setCollection] = useState<ThemeCollection>(initialCollection)
  const [confetti, setConfetti] = useState<ConfettiBurst | null>(null)
  const [worldCupSearch, setWorldCupSearch] = useState('')
  const [worldCupContinent, setWorldCupContinent] = useState('all')

  const worldCupContinents = useMemo(
    () =>
      Array.from(
        new Set(WORLD_CUP_THEME_OPTIONS.map((theme) => getWorldCupContinent(theme)).filter(Boolean)),
      ).sort(),
    [],
  )

  const visibleThemes = useMemo(() => {
    if (collection === 'classic') return CLASSIC_THEME_OPTIONS

    const searchTerm = normalizeThemeSearch(worldCupSearch)
    return WORLD_CUP_THEME_OPTIONS
      .filter((theme) => {
        const continent = getWorldCupContinent(theme)
        const matchesContinent = worldCupContinent === 'all' || continent === worldCupContinent
        const matchesSearch =
          !searchTerm ||
          normalizeThemeSearch(theme.name).includes(searchTerm) ||
          normalizeThemeSearch(theme.description).includes(searchTerm)

        return matchesContinent && matchesSearch
      })
      .sort((current, next) => current.name.localeCompare(next.name, 'pt-BR'))
  }, [collection, worldCupContinent, worldCupSearch])

  function handleThemeSelect(theme: ThemeOption) {
    const shouldCelebrate = theme.category === 'world-cup' && theme.id !== themeId
    setThemeId(theme.id)
    if (shouldCelebrate) {
      setConfetti({
        id: Date.now(),
        colors: theme.preview?.colors ?? [
          theme.colors.primary,
          theme.colors.secondary,
          theme.colors.card,
        ],
      })
    }
  }

  return (
    <div className="flex h-screen flex-col bg-surface">
      {confetti && (
        <WorldCupConfetti
          burst={confetti}
          onDone={() => setConfetti(null)}
        />
      )}
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
                  Alterne rapidamente entre a base clara e escura principal.
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
            <div className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <h2 className="text-base font-black text-stone-900">Temas visuais</h2>
                <p className="mt-1 text-sm font-medium text-stone-500">
                  Escolha uma identidade completa para cores, fundos, cards, tabelas, formularios e menus.
                </p>
              </div>
              <ThemeCollectionToggle
                value={collection}
                onChange={setCollection}
              />
            </div>

            {collection === 'world-cup' && (
              <>
                <WorldCupHeader />
                <WorldCupControls
                  continents={worldCupContinents}
                  search={worldCupSearch}
                  selectedContinent={worldCupContinent}
                  totalCount={WORLD_CUP_THEME_OPTIONS.length}
                  visibleCount={visibleThemes.length}
                  onContinentChange={setWorldCupContinent}
                  onSearchChange={setWorldCupSearch}
                />
              </>
            )}

            <div className="mb-4 flex items-center justify-between gap-3">
              <p className="text-xs font-bold uppercase tracking-wide text-stone-400">
                {visibleThemes.length} opcoes
              </p>
              {collection === 'world-cup' && (
                <span className="inline-flex items-center gap-1.5 rounded-full border border-brand-200 bg-brand-50 px-3 py-1 text-[11px] font-black uppercase text-brand-700">
                  <Trophy className="size-3.5" strokeWidth={2.2} />
                  Copa do Mundo
                </span>
              )}
            </div>

            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
              {visibleThemes.map((theme) => (
                <ThemeCard
                  key={theme.id}
                  theme={theme}
                  selected={theme.id === themeId}
                  onSelect={() => handleThemeSelect(theme)}
                />
              ))}
            </div>

            {visibleThemes.length === 0 && (
              <div className="rounded-lg border border-dashed border-stone-300 bg-stone-50 p-8 text-center">
                <p className="text-sm font-black text-stone-900">Nenhuma selecao encontrada</p>
                <p className="mt-1 text-sm font-medium text-stone-500">
                  Ajuste a busca ou selecione outro continente.
                </p>
              </div>
            )}
          </section>
        </div>
      </main>
    </div>
  )
}

type ThemeCollection = 'classic' | 'world-cup'

interface ConfettiBurst {
  id: number
  colors: string[]
}

const WORLD_CUP_THEME_CONTINENTS: Record<string, string> = {
  'world-cup-france': 'UEFA',
  'world-cup-spain': 'UEFA',
  'world-cup-argentina': 'CONMEBOL',
  'world-cup-england': 'UEFA',
  'world-cup-brazil': 'CONMEBOL',
  'world-cup-portugal': 'UEFA',
  'world-cup-germany': 'UEFA',
  'world-cup-netherlands': 'UEFA',
  'world-cup-belgium': 'UEFA',
  'world-cup-uruguay': 'CONMEBOL',
  'world-cup-colombia': 'CONMEBOL',
  'world-cup-croatia': 'UEFA',
}

function getWorldCupContinent(theme: ThemeOption) {
  return theme.continent ?? WORLD_CUP_THEME_CONTINENTS[theme.id] ?? 'Outros'
}

function normalizeThemeSearch(value: string) {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim()
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

function ThemeCollectionToggle({
  value,
  onChange,
}: {
  value: ThemeCollection
  onChange: (value: ThemeCollection) => void
}) {
  return (
    <div className="grid w-full max-w-md grid-cols-2 rounded-full bg-stone-100 p-1">
      {[
        ['classic', 'Temas Classicos'],
        ['world-cup', 'Copa do Mundo'],
      ].map(([key, label]) => (
        <button
          key={key}
          type="button"
          onClick={() => onChange(key as ThemeCollection)}
          className={[
            'rounded-full px-3 py-1.5 text-xs font-black transition',
            value === key
              ? 'bg-white text-stone-950 shadow-sm'
              : 'text-stone-600 hover:text-stone-900',
          ].join(' ')}
        >
          {label}
        </button>
      ))}
    </div>
  )
}

function WorldCupHeader() {
  return (
    <section className="mb-5 overflow-hidden rounded-lg border border-brand-100 bg-brand-50">
      <div className="flex flex-col gap-4 p-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 items-center gap-3">
          <span className="flex size-12 flex-shrink-0 items-center justify-center rounded-lg bg-white text-brand-700">
            <Trophy className="size-6" strokeWidth={2.2} />
          </span>
          <div className="min-w-0">
            <p className="text-[11px] font-black uppercase tracking-wide text-brand-700">
              Copa 2026
            </p>
            <h3 className="truncate text-base font-black text-stone-900">
              Temas inspirados em selecoes
            </h3>
          </div>
        </div>
        <div className="grid grid-cols-4 gap-1.5 sm:w-40">
          {['#1F3C88', '#F7D117', '#C60B1E', '#5BA7D9'].map((color) => (
            <span
              key={color}
              className="h-7 rounded-md border border-white/70"
              style={{ background: color }}
            />
          ))}
        </div>
      </div>
    </section>
  )
}

function WorldCupControls({
  continents,
  search,
  selectedContinent,
  totalCount,
  visibleCount,
  onContinentChange,
  onSearchChange,
}: {
  continents: string[]
  search: string
  selectedContinent: string
  totalCount: number
  visibleCount: number
  onContinentChange: (continent: string) => void
  onSearchChange: (search: string) => void
}) {
  return (
    <div className="mb-5 rounded-lg border border-stone-200 bg-stone-50 p-3">
      <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_220px_auto] lg:items-center">
        <label className="relative block">
          <span className="sr-only">Buscar selecao</span>
          <Search
            className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-stone-400"
            strokeWidth={2}
          />
          <input
            value={search}
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder="Buscar selecao"
            className="h-10 w-full rounded-md border border-stone-200 bg-white pl-9 pr-3 text-sm font-semibold text-stone-900 outline-none transition placeholder:text-stone-400 focus:border-brand-600"
          />
        </label>

        <label className="block">
          <span className="sr-only">Filtrar por continente</span>
          <select
            value={selectedContinent}
            onChange={(event) => onContinentChange(event.target.value)}
            className="h-10 w-full rounded-md border border-stone-200 bg-white px-3 text-sm font-black text-stone-700 outline-none transition focus:border-brand-600"
          >
            <option value="all">Todos</option>
            {continents.map((continent) => (
              <option key={continent} value={continent}>
                {continent}
              </option>
            ))}
          </select>
        </label>

        <div className="rounded-md border border-brand-100 bg-white px-3 py-2 text-xs font-black uppercase text-brand-700">
          {visibleCount} de {totalCount}
        </div>
      </div>
    </div>
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
            {theme.category === 'world-cup' ? (
              <span className="inline-flex items-center gap-1 rounded-full bg-brand-50 px-2 py-0.5 text-[10px] font-black uppercase text-brand-700">
                <Trophy className="size-3" strokeWidth={2.2} />
                Copa
              </span>
            ) : (
              <span className="rounded-full bg-stone-100 px-2 py-0.5 text-[10px] font-black uppercase text-stone-500">
                {theme.mode}
              </span>
            )}
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
  const swatches = theme.preview?.colors ?? [
    theme.colors.primary,
    theme.colors.secondary,
    theme.colors.card,
  ]

  return (
    <div
      className="border-b border-stone-200 p-4"
      style={{ background: getPreviewBackground(theme) }}
    >
      <div className="flex items-center gap-2">
        {swatches.slice(0, 3).map((color) => (
          <span
            key={color}
            className="size-3 rounded-full border border-white/60"
            style={{ background: color }}
          />
        ))}
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
            style={{ background: swatches[0] ?? theme.colors.primary }}
          />
          <div
            className="h-8 w-12 rounded-md"
            style={{ background: swatches[1] ?? theme.colors.secondary }}
          />
        </div>
      </div>
    </div>
  )
}

function getPreviewBackground(theme: ThemeOption) {
  const colors = theme.preview?.colors ?? [
    theme.colors.surface,
    theme.colors.primary,
    theme.colors.secondary,
  ]
  const [first, second, third = theme.colors.secondary, fourth = third] = colors

  switch (theme.preview?.pattern) {
    case 'checker':
      return `conic-gradient(${first} 25%, ${second} 0 50%, ${first} 0 75%, ${second} 0) 0 / 30px 30px`
    case 'cross':
      return `linear-gradient(90deg, transparent 0 42%, ${second} 42% 58%, transparent 58%), linear-gradient(0deg, ${first} 0 42%, ${second} 42% 58%, ${first} 58%)`
    case 'stripes':
      return `repeating-linear-gradient(90deg, ${first} 0 26px, ${second} 26px 52px), linear-gradient(135deg, ${third}, ${first})`
    case 'bands':
      return `linear-gradient(135deg, ${first} 0 42%, ${second} 42% 58%, ${third} 58% 82%, ${fourth} 82%)`
    default:
      return theme.colors.surface
  }
}

function WorldCupConfetti({
  burst,
  onDone,
}: {
  burst: ConfettiBurst
  onDone: () => void
}) {
  useEffect(() => {
    const timeoutId = window.setTimeout(onDone, 3100)
    return () => window.clearTimeout(timeoutId)
  }, [burst.id, onDone])

  const pieces = useMemo(
    () =>
      Array.from({ length: 96 }, (_, index) => ({
        color: burst.colors[index % burst.colors.length],
        delay: (index % 12) * 45,
        drift: ((index * 37) % 260) - 130,
        left: 2 + ((index * 19) % 96),
        rotate: 180 + ((index * 47) % 360),
        width: 6 + (index % 3) * 3,
      })),
    [burst],
  )

  return (
    <div
      key={burst.id}
      className="pointer-events-none fixed inset-0 z-[80] overflow-hidden"
      aria-hidden="true"
    >
      {pieces.map((piece, index) => (
        <span
          key={`${burst.id}-${index}`}
          className="world-cup-confetti-piece"
          style={{
            '--confetti-x': `${piece.drift}px`,
            '--confetti-rotate': `${piece.rotate}deg`,
            animationDelay: `${piece.delay}ms`,
            background: piece.color,
            height: `${piece.width + 4}px`,
            left: `${piece.left}%`,
            width: `${piece.width}px`,
          } as CSSProperties}
        />
      ))}
    </div>
  )
}
