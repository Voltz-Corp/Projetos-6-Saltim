import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

export type AppearanceMode = 'light' | 'dark'
export type ThemeCategory = 'classic' | 'world-cup'
export type ThemePreviewPattern = 'bands' | 'checker' | 'cross' | 'stripes'

export interface ThemeOption {
  id: string
  name: string
  mode: AppearanceMode
  category: ThemeCategory
  description: string
  preview?: {
    colors: string[]
    pattern?: ThemePreviewPattern
  }
  colors: {
    surface: string
    card: string
    primary: string
    secondary: string
    text: string
  }
}

export const CLASSIC_THEME_OPTIONS: ThemeOption[] = [
  {
    id: 'maestro-light',
    name: 'Maestro Light',
    mode: 'light',
    category: 'classic',
    description: 'Identidade Maestro clara',
    colors: {
      surface: '#F6F5FB',
      card: '#FFFFFF',
      primary: '#1B1464',
      secondary: '#F15A24',
      text: '#211F33',
    },
  },
  {
    id: 'maestro-dark',
    name: 'Maestro Dark',
    mode: 'dark',
    category: 'classic',
    description: 'Identidade Maestro escura',
    colors: {
      surface: '#141127',
      card: '#1E1A33',
      primary: '#F15A24',
      secondary: '#8E7CFF',
      text: '#F5F3FF',
    },
  },
  {
    id: 'saltim-light',
    name: 'Saltim Light',
    mode: 'light',
    category: 'classic',
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
    name: 'Saltim Dark',
    mode: 'dark',
    category: 'classic',
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
    id: 'mossy-forest-light-green',
    name: 'Mossy Forest Light Green',
    mode: 'light',
    category: 'classic',
    description: 'Verde claro natural e suave',
    colors: {
      surface: '#F1F5E0',
      card: '#F7FAF0',
      primary: '#3D5436',
      secondary: '#A46122',
      text: '#2C3320',
    },
  },
  {
    id: 'anime-trinity-one-piece-dark',
    name: 'Anime Trinity One Piece',
    mode: 'dark',
    category: 'classic',
    description: 'Marinho escuro com vermelho, azul e dourado',
    colors: {
      surface: '#0F172A',
      card: '#172036',
      primary: '#EF4444',
      secondary: '#FBBF24',
      text: '#E2E8F0',
    },
  },
  {
    id: 'dracula',
    name: 'Dracula',
    mode: 'dark',
    category: 'classic',
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
    category: 'classic',
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
    category: 'classic',
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
    category: 'classic',
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
    category: 'classic',
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
    category: 'classic',
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
    category: 'classic',
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
    category: 'classic',
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
    category: 'classic',
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

export const WORLD_CUP_THEME_OPTIONS: ThemeOption[] = [
  {
    id: 'world-cup-france',
    name: 'Franca',
    mode: 'dark',
    category: 'world-cup',
    description: 'Azul tradicional com branco e vermelho',
    preview: { colors: ['#172A68', '#FFFFFF', '#EF3340'], pattern: 'bands' },
    colors: {
      surface: '#0C1633',
      card: '#142350',
      primary: '#1F3C88',
      secondary: '#EF3340',
      text: '#F8FAFC',
    },
  },
  {
    id: 'world-cup-spain',
    name: 'Espanha',
    mode: 'light',
    category: 'world-cup',
    description: 'Vermelho vibrante com dourado intenso',
    preview: { colors: ['#C60B1E', '#FFC400', '#8A0714'], pattern: 'bands' },
    colors: {
      surface: '#FFF4D6',
      card: '#FFFFFF',
      primary: '#C60B1E',
      secondary: '#FFC400',
      text: '#2A1010',
    },
  },
  {
    id: 'world-cup-argentina',
    name: 'Argentina',
    mode: 'light',
    category: 'world-cup',
    description: 'Listras celestes e brancas com dourado',
    preview: { colors: ['#75AADB', '#FFFFFF', '#F6B40E'], pattern: 'stripes' },
    colors: {
      surface: '#E9F5FF',
      card: '#FFFFFF',
      primary: '#5BA7D9',
      secondary: '#D6A21F',
      text: '#14213D',
    },
  },
  {
    id: 'world-cup-england',
    name: 'Inglaterra',
    mode: 'light',
    category: 'world-cup',
    description: 'Base branca classica com vermelho e marinho',
    preview: { colors: ['#FFFFFF', '#CF142B', '#1D2A57'], pattern: 'cross' },
    colors: {
      surface: '#F7F8FB',
      card: '#FFFFFF',
      primary: '#CF142B',
      secondary: '#1D2A57',
      text: '#111827',
    },
  },
  {
    id: 'world-cup-brazil',
    name: 'Brasil',
    mode: 'light',
    category: 'world-cup',
    description: 'Amarelo canarinho com verde e azul',
    preview: { colors: ['#FFDF00', '#009C3B', '#002776'], pattern: 'bands' },
    colors: {
      surface: '#FFF8CC',
      card: '#FFFFFF',
      primary: '#F7D117',
      secondary: '#009C3B',
      text: '#132A13',
    },
  },
  {
    id: 'world-cup-portugal',
    name: 'Portugal',
    mode: 'dark',
    category: 'world-cup',
    description: 'Vermelho escuro com verde e dourado',
    preview: { colors: ['#7A0019', '#006A44', '#D4AF37'], pattern: 'bands' },
    colors: {
      surface: '#21070D',
      card: '#371017',
      primary: '#9B1028',
      secondary: '#00835C',
      text: '#FFF7E6',
    },
  },
  {
    id: 'world-cup-germany',
    name: 'Alemanha',
    mode: 'light',
    category: 'world-cup',
    description: 'Branco sobrio com preto, vermelho e dourado',
    preview: { colors: ['#FFFFFF', '#111111', '#DD0000', '#FFCE00'], pattern: 'bands' },
    colors: {
      surface: '#F4F4F2',
      card: '#FFFFFF',
      primary: '#111111',
      secondary: '#D4A000',
      text: '#18181B',
    },
  },
  {
    id: 'world-cup-netherlands',
    name: 'Holanda',
    mode: 'light',
    category: 'world-cup',
    description: 'Laranja forte com marinho e branco',
    preview: { colors: ['#FF6F00', '#102B5C', '#FFFFFF'], pattern: 'bands' },
    colors: {
      surface: '#FFF0E4',
      card: '#FFFFFF',
      primary: '#F36C21',
      secondary: '#102B5C',
      text: '#23150D',
    },
  },
  {
    id: 'world-cup-belgium',
    name: 'Belgica',
    mode: 'dark',
    category: 'world-cup',
    description: 'Vermelho belga com preto e dourado',
    preview: { colors: ['#E30613', '#111111', '#FFD90C'], pattern: 'bands' },
    colors: {
      surface: '#1C0708',
      card: '#2D0D10',
      primary: '#E30613',
      secondary: '#FFD90C',
      text: '#FFF5F5',
    },
  },
  {
    id: 'world-cup-uruguay',
    name: 'Uruguai',
    mode: 'light',
    category: 'world-cup',
    description: 'Celeste tradicional com branco e dourado',
    preview: { colors: ['#5CBFEB', '#FFFFFF', '#D8A31A'], pattern: 'stripes' },
    colors: {
      surface: '#EAF8FF',
      card: '#FFFFFF',
      primary: '#4BB6E8',
      secondary: '#D8A31A',
      text: '#123047',
    },
  },
  {
    id: 'world-cup-colombia',
    name: 'Colombia',
    mode: 'light',
    category: 'world-cup',
    description: 'Amarelo vibrante com azul e vermelho',
    preview: { colors: ['#FCD116', '#003893', '#CE1126'], pattern: 'bands' },
    colors: {
      surface: '#FFF7C2',
      card: '#FFFFFF',
      primary: '#F7C600',
      secondary: '#003893',
      text: '#1F1B0A',
    },
  },
  {
    id: 'world-cup-croatia',
    name: 'Croacia',
    mode: 'light',
    category: 'world-cup',
    description: 'Xadrez vermelho e branco da selecao croata',
    preview: { colors: ['#F7F7F7', '#D20A11', '#171796'], pattern: 'checker' },
    colors: {
      surface: '#FFF1F1',
      card: '#FFFFFF',
      primary: '#D20A11',
      secondary: '#171796',
      text: '#1F1720',
    },
  },
]

export const THEME_OPTIONS: ThemeOption[] = [
  ...CLASSIC_THEME_OPTIONS,
  ...WORLD_CUP_THEME_OPTIONS,
]

const STORAGE_KEY = 'saltim-appearance-theme'
const DEFAULT_THEME = 'maestro-light'

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
        setThemeIdState(mode === 'light' ? 'maestro-light' : 'maestro-dark'),
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
