import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

export type AppearanceMode = 'light' | 'dark'

export interface ThemeOption {
  id: string
  name: string
  mode: AppearanceMode
  description: string
  colors: {
    surface: string
    card: string
    primary: string
    secondary: string
    text: string
  }
}

export const THEME_OPTIONS: ThemeOption[] = [
  {
    id: 'saltim-light',
    name: 'Light',
    mode: 'light',
    description: 'Padrao Saltim claro',
    colors: {
      surface: '#F5F4F1',
      card: '#FFFFFF',
      primary: '#F07820',
      secondary: '#2D7A3A',
      text: '#1A1918',
    },
  },
  {
    id: 'saltim-dark',
    name: 'Dark',
    mode: 'dark',
    description: 'Saltim em modo escuro',
    colors: {
      surface: '#11100F',
      card: '#1C1917',
      primary: '#F59E42',
      secondary: '#52B9EB',
      text: '#F5F5F4',
    },
  },
  {
    id: 'dracula',
    name: 'Dracula',
    mode: 'dark',
    description: 'Roxo, rosa e contraste alto',
    colors: {
      surface: '#282A36',
      card: '#343746',
      primary: '#BD93F9',
      secondary: '#FF79C6',
      text: '#F8F8F2',
    },
  },
  {
    id: 'nord',
    name: 'Nord',
    mode: 'dark',
    description: 'Azuis frios e suaves',
    colors: {
      surface: '#2E3440',
      card: '#3B4252',
      primary: '#88C0D0',
      secondary: '#A3BE8C',
      text: '#ECEFF4',
    },
  },
  {
    id: 'solarized-dark',
    name: 'Solarized Dark',
    mode: 'dark',
    description: 'Base escura solarizada',
    colors: {
      surface: '#002B36',
      card: '#073642',
      primary: '#268BD2',
      secondary: '#B58900',
      text: '#EEE8D5',
    },
  },
  {
    id: 'solarized-light',
    name: 'Solarized Light',
    mode: 'light',
    description: 'Base clara solarizada',
    colors: {
      surface: '#FDF6E3',
      card: '#FFFBEA',
      primary: '#268BD2',
      secondary: '#859900',
      text: '#073642',
    },
  },
  {
    id: 'monokai',
    name: 'Monokai',
    mode: 'dark',
    description: 'Editor classico vibrante',
    colors: {
      surface: '#272822',
      card: '#34352D',
      primary: '#A6E22E',
      secondary: '#FD971F',
      text: '#F8F8F2',
    },
  },
  {
    id: 'github-dark',
    name: 'GitHub Dark',
    mode: 'dark',
    description: 'Neutro escuro e azul',
    colors: {
      surface: '#0D1117',
      card: '#161B22',
      primary: '#58A6FF',
      secondary: '#3FB950',
      text: '#F0F6FC',
    },
  },
  {
    id: 'cyberpunk',
    name: 'Cyberpunk',
    mode: 'dark',
    description: 'Neon amarelo e magenta',
    colors: {
      surface: '#09090F',
      card: '#171421',
      primary: '#FCEE0A',
      secondary: '#FF2A6D',
      text: '#F8FAFC',
    },
  },
  {
    id: 'forest',
    name: 'Forest',
    mode: 'dark',
    description: 'Verdes profundos',
    colors: {
      surface: '#0F1F17',
      card: '#173526',
      primary: '#7DD87D',
      secondary: '#D6A85B',
      text: '#EFF7ED',
    },
  },
  {
    id: 'ocean',
    name: 'Ocean',
    mode: 'dark',
    description: 'Azul profundo e ciano',
    colors: {
      surface: '#071A2C',
      card: '#0B2540',
      primary: '#38BDF8',
      secondary: '#2DD4BF',
      text: '#E0F2FE',
    },
  },
]

const STORAGE_KEY = 'saltim-appearance-theme'
const DEFAULT_THEME = 'saltim-light'

interface AppearanceContextValue {
  themeId: string
  theme: ThemeOption
  mode: AppearanceMode
  setThemeId: (themeId: string) => void
  setMode: (mode: AppearanceMode) => void
}

const AppearanceContext = createContext<AppearanceContextValue | null>(null)

function resolveTheme(themeId: string | null | undefined) {
  return THEME_OPTIONS.find((theme) => theme.id === themeId) ?? THEME_OPTIONS[0]
}

export function AppearanceProvider({ children }: { children: ReactNode }) {
  const [themeId, setThemeIdState] = useState(() => {
    if (typeof window === 'undefined') return DEFAULT_THEME
    return resolveTheme(window.localStorage.getItem(STORAGE_KEY)).id
  })

  const theme = resolveTheme(themeId)

  useEffect(() => {
    const root = document.documentElement
    root.dataset.theme = theme.id
    root.dataset.mode = theme.mode
    root.style.colorScheme = theme.mode
    window.localStorage.setItem(STORAGE_KEY, theme.id)
  }, [theme])

  const value = useMemo<AppearanceContextValue>(
    () => ({
      themeId: theme.id,
      theme,
      mode: theme.mode,
      setThemeId: (nextThemeId) => setThemeIdState(resolveTheme(nextThemeId).id),
      setMode: (mode) =>
        setThemeIdState(mode === 'light' ? 'saltim-light' : 'saltim-dark'),
    }),
    [theme],
  )

  return (
    <AppearanceContext.Provider value={value}>
      {children}
    </AppearanceContext.Provider>
  )
}

export function useAppearance() {
  const value = useContext(AppearanceContext)
  if (!value) {
    throw new Error('useAppearance must be used inside AppearanceProvider')
  }
  return value
}
