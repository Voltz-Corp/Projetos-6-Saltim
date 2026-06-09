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
  continent?: string
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
  {
    id: 'world-cup-mexico',
    name: 'Mexico',
    mode: 'light',
    category: 'world-cup',
    continent: 'CONCACAF',
    description: 'Verde mexicano com branco e vermelho',
    preview: { colors: ['#006847', '#FFFFFF', '#CE1126'], pattern: 'bands' },
    colors: {
      surface: '#EAF7EF',
      card: '#FFFFFF',
      primary: '#006847',
      secondary: '#CE1126',
      text: '#102A20',
    },
  },
  {
    id: 'world-cup-czechia',
    name: 'Tchequia',
    mode: 'light',
    category: 'world-cup',
    continent: 'UEFA',
    description: 'Vermelho tcheco com azul e branco',
    preview: { colors: ['#D7141A', '#11457E', '#FFFFFF'], pattern: 'bands' },
    colors: {
      surface: '#FFF1F2',
      card: '#FFFFFF',
      primary: '#D7141A',
      secondary: '#11457E',
      text: '#1E1720',
    },
  },
  {
    id: 'world-cup-south-africa',
    name: 'Africa do Sul',
    mode: 'dark',
    category: 'world-cup',
    continent: 'CAF',
    description: 'Dourado e verde vibrantes da selecao sul-africana',
    preview: { colors: ['#FFB612', '#007A4D', '#000000', '#FFFFFF'], pattern: 'bands' },
    colors: {
      surface: '#152414',
      card: '#20351E',
      primary: '#FFB612',
      secondary: '#007A4D',
      text: '#FFFBEA',
    },
  },
  {
    id: 'world-cup-south-korea',
    name: 'Coreia do Sul',
    mode: 'light',
    category: 'world-cup',
    continent: 'AFC',
    description: 'Vermelho vivo com azul e branco modernos',
    preview: { colors: ['#E6002D', '#0047A0', '#FFFFFF'], pattern: 'bands' },
    colors: {
      surface: '#FFF1F4',
      card: '#FFFFFF',
      primary: '#E6002D',
      secondary: '#0047A0',
      text: '#1B1D2A',
    },
  },
  {
    id: 'world-cup-canada',
    name: 'Canada',
    mode: 'light',
    category: 'world-cup',
    continent: 'CONCACAF',
    description: 'Vermelho e branco limpos da identidade canadense',
    preview: { colors: ['#FF0000', '#FFFFFF', '#C8102E'], pattern: 'cross' },
    colors: {
      surface: '#FFF5F5',
      card: '#FFFFFF',
      primary: '#C8102E',
      secondary: '#FFFFFF',
      text: '#221112',
    },
  },
  {
    id: 'world-cup-bosnia-herzegovina',
    name: 'Bosnia e Herzegovina',
    mode: 'dark',
    category: 'world-cup',
    continent: 'UEFA',
    description: 'Azul profundo com dourado e branco da bandeira',
    preview: { colors: ['#002F6C', '#FECB00', '#FFFFFF'], pattern: 'bands' },
    colors: {
      surface: '#081B3A',
      card: '#102A55',
      primary: '#1E5AA8',
      secondary: '#FECB00',
      text: '#F8FBFF',
    },
  },
  {
    id: 'world-cup-qatar',
    name: 'Catar',
    mode: 'dark',
    category: 'world-cup',
    continent: 'AFC',
    description: 'Bordo elegante com branco da selecao catari',
    preview: { colors: ['#8A1538', '#FFFFFF', '#5B0F28'], pattern: 'bands' },
    colors: {
      surface: '#240711',
      card: '#3A0E20',
      primary: '#8A1538',
      secondary: '#FFFFFF',
      text: '#FFF5F8',
    },
  },
  {
    id: 'world-cup-switzerland',
    name: 'Suica',
    mode: 'light',
    category: 'world-cup',
    continent: 'UEFA',
    description: 'Vermelho forte com branco da bandeira suica',
    preview: { colors: ['#D52B1E', '#FFFFFF', '#B61F16'], pattern: 'cross' },
    colors: {
      surface: '#FFF2F0',
      card: '#FFFFFF',
      primary: '#D52B1E',
      secondary: '#FFFFFF',
      text: '#241312',
    },
  },
  {
    id: 'world-cup-haiti',
    name: 'Haiti',
    mode: 'dark',
    category: 'world-cup',
    continent: 'CONCACAF',
    description: 'Azul e vermelho de alto contraste da bandeira haitiana',
    preview: { colors: ['#00209F', '#D21034', '#FFFFFF'], pattern: 'bands' },
    colors: {
      surface: '#07133E',
      card: '#101F55',
      primary: '#1647B8',
      secondary: '#D21034',
      text: '#F8FAFF',
    },
  },
  {
    id: 'world-cup-morocco',
    name: 'Marrocos',
    mode: 'dark',
    category: 'world-cup',
    continent: 'CAF',
    description: 'Vermelho tradicional com verde marroquino',
    preview: { colors: ['#C1272D', '#006233', '#8A1A20'], pattern: 'bands' },
    colors: {
      surface: '#28080A',
      card: '#3B1013',
      primary: '#C1272D',
      secondary: '#00A651',
      text: '#FFF5F5',
    },
  },
  {
    id: 'world-cup-scotland',
    name: 'Escocia',
    mode: 'dark',
    category: 'world-cup',
    continent: 'UEFA',
    description: 'Azul escuro com branco e leitura tartan discreta',
    preview: { colors: ['#002B5C', '#FFFFFF', '#1B365D'], pattern: 'cross' },
    colors: {
      surface: '#081528',
      card: '#10233F',
      primary: '#1B365D',
      secondary: '#FFFFFF',
      text: '#F8FAFC',
    },
  },
  {
    id: 'world-cup-united-states',
    name: 'Estados Unidos',
    mode: 'dark',
    category: 'world-cup',
    continent: 'CONCACAF',
    description: 'Marinho esportivo com vermelho e branco',
    preview: { colors: ['#1D3557', '#FFFFFF', '#E63946'], pattern: 'stripes' },
    colors: {
      surface: '#0B1629',
      card: '#14233A',
      primary: '#1D3557',
      secondary: '#E63946',
      text: '#F8FAFC',
    },
  },
  {
    id: 'world-cup-australia',
    name: 'Australia',
    mode: 'light',
    category: 'world-cup',
    continent: 'AFC',
    description: 'Dourado australiano com verde esportivo',
    preview: { colors: ['#FFCD00', '#00843D', '#FFFFFF'], pattern: 'bands' },
    colors: {
      surface: '#FFF8D6',
      card: '#FFFFFF',
      primary: '#FFCD00',
      secondary: '#00843D',
      text: '#1E2A12',
    },
  },
  {
    id: 'world-cup-paraguay',
    name: 'Paraguai',
    mode: 'light',
    category: 'world-cup',
    continent: 'CONMEBOL',
    description: 'Vermelho, branco e azul da camisa tradicional',
    preview: { colors: ['#D52B1E', '#FFFFFF', '#0038A8'], pattern: 'stripes' },
    colors: {
      surface: '#FFF4F4',
      card: '#FFFFFF',
      primary: '#D52B1E',
      secondary: '#0038A8',
      text: '#1D1B2A',
    },
  },
  {
    id: 'world-cup-turkey',
    name: 'Turquia',
    mode: 'dark',
    category: 'world-cup',
    continent: 'UEFA',
    description: 'Vermelho intenso com branco da bandeira turca',
    preview: { colors: ['#E30A17', '#FFFFFF', '#A80712'], pattern: 'bands' },
    colors: {
      surface: '#2A070A',
      card: '#400E13',
      primary: '#E30A17',
      secondary: '#FFFFFF',
      text: '#FFF5F5',
    },
  },
  {
    id: 'world-cup-curacao',
    name: 'Curacao',
    mode: 'dark',
    category: 'world-cup',
    continent: 'CONCACAF',
    description: 'Azul tropical com amarelo e branco vibrantes',
    preview: { colors: ['#002B7F', '#F9D616', '#FFFFFF'], pattern: 'bands' },
    colors: {
      surface: '#071A3F',
      card: '#102A5C',
      primary: '#0061A8',
      secondary: '#F9D616',
      text: '#F8FBFF',
    },
  },
  {
    id: 'world-cup-ecuador',
    name: 'Equador',
    mode: 'light',
    category: 'world-cup',
    continent: 'CONMEBOL',
    description: 'Amarelo equatoriano com azul e vermelho',
    preview: { colors: ['#FFD100', '#003893', '#CE1126'], pattern: 'bands' },
    colors: {
      surface: '#FFF7CC',
      card: '#FFFFFF',
      primary: '#FFD100',
      secondary: '#003893',
      text: '#211A08',
    },
  },
  {
    id: 'world-cup-ivory-coast',
    name: 'Costa do Marfim',
    mode: 'light',
    category: 'world-cup',
    continent: 'CAF',
    description: 'Laranja marfinense com verde e branco',
    preview: { colors: ['#F77F00', '#FFFFFF', '#009E60'], pattern: 'bands' },
    colors: {
      surface: '#FFF1E3',
      card: '#FFFFFF',
      primary: '#F77F00',
      secondary: '#009E60',
      text: '#24180E',
    },
  },
  {
    id: 'world-cup-japan',
    name: 'Japao',
    mode: 'dark',
    category: 'world-cup',
    continent: 'AFC',
    description: 'Azul samurai com branco e vermelho',
    preview: { colors: ['#003F88', '#FFFFFF', '#BC002D'], pattern: 'bands' },
    colors: {
      surface: '#071933',
      card: '#102A4C',
      primary: '#003F88',
      secondary: '#BC002D',
      text: '#F8FAFC',
    },
  },
  {
    id: 'world-cup-sweden',
    name: 'Suecia',
    mode: 'dark',
    category: 'world-cup',
    continent: 'UEFA',
    description: 'Azul sueco com amarelo de alto contraste',
    preview: { colors: ['#006AA7', '#FECC00', '#004B7A'], pattern: 'cross' },
    colors: {
      surface: '#071E32',
      card: '#102F4A',
      primary: '#006AA7',
      secondary: '#FECC00',
      text: '#F5FAFF',
    },
  },
  {
    id: 'world-cup-tunisia',
    name: 'Tunisia',
    mode: 'light',
    category: 'world-cup',
    continent: 'CAF',
    description: 'Vermelho e branco limpos da identidade tunisiana',
    preview: { colors: ['#E70013', '#FFFFFF', '#C90010'], pattern: 'bands' },
    colors: {
      surface: '#FFF1F2',
      card: '#FFFFFF',
      primary: '#E70013',
      secondary: '#FFFFFF',
      text: '#221112',
    },
  },
  {
    id: 'world-cup-egypt',
    name: 'Egito',
    mode: 'dark',
    category: 'world-cup',
    continent: 'CAF',
    description: 'Vermelho egipcio com preto, branco e dourado',
    preview: { colors: ['#CE1126', '#FFFFFF', '#000000', '#C09300'], pattern: 'bands' },
    colors: {
      surface: '#1F0D10',
      card: '#2D1618',
      primary: '#CE1126',
      secondary: '#C09300',
      text: '#FFF7ED',
    },
  },
  {
    id: 'world-cup-iran',
    name: 'Ira',
    mode: 'light',
    category: 'world-cup',
    continent: 'AFC',
    description: 'Base branca com verde e vermelho nacionais',
    preview: { colors: ['#FFFFFF', '#239F40', '#DA0000'], pattern: 'bands' },
    colors: {
      surface: '#F7FFF8',
      card: '#FFFFFF',
      primary: '#239F40',
      secondary: '#DA0000',
      text: '#15231A',
    },
  },
  {
    id: 'world-cup-new-zealand',
    name: 'Nova Zelandia',
    mode: 'dark',
    category: 'world-cup',
    continent: 'OFC',
    description: 'Preto sobrio com branco da identidade esportiva',
    preview: { colors: ['#111111', '#FFFFFF', '#2D3748'], pattern: 'bands' },
    colors: {
      surface: '#0B0B0B',
      card: '#181818',
      primary: '#111111',
      secondary: '#FFFFFF',
      text: '#F8FAFC',
    },
  },
  {
    id: 'world-cup-cape-verde',
    name: 'Cabo Verde',
    mode: 'dark',
    category: 'world-cup',
    continent: 'CAF',
    description: 'Azul leve com vermelho, branco e amarelo',
    preview: { colors: ['#003893', '#FFFFFF', '#CF2027', '#F7D117'], pattern: 'stripes' },
    colors: {
      surface: '#071B3D',
      card: '#102B5C',
      primary: '#003893',
      secondary: '#F7D117',
      text: '#F8FBFF',
    },
  },
  {
    id: 'world-cup-saudi-arabia',
    name: 'Arabia Saudita',
    mode: 'dark',
    category: 'world-cup',
    continent: 'AFC',
    description: 'Verde saudita tradicional com branco',
    preview: { colors: ['#006C35', '#FFFFFF', '#004B25'], pattern: 'bands' },
    colors: {
      surface: '#062416',
      card: '#0D3923',
      primary: '#006C35',
      secondary: '#FFFFFF',
      text: '#F4FFF8',
    },
  },
  {
    id: 'world-cup-norway',
    name: 'Noruega',
    mode: 'light',
    category: 'world-cup',
    continent: 'UEFA',
    description: 'Vermelho noruegues com azul escuro e branco',
    preview: { colors: ['#BA0C2F', '#FFFFFF', '#00205B'], pattern: 'cross' },
    colors: {
      surface: '#FFF2F4',
      card: '#FFFFFF',
      primary: '#BA0C2F',
      secondary: '#00205B',
      text: '#1E1720',
    },
  },
  {
    id: 'world-cup-senegal',
    name: 'Senegal',
    mode: 'dark',
    category: 'world-cup',
    continent: 'CAF',
    description: 'Verde senegales com amarelo e vermelho vibrantes',
    preview: { colors: ['#00853F', '#FDEF42', '#E31B23'], pattern: 'bands' },
    colors: {
      surface: '#062314',
      card: '#0E3A23',
      primary: '#00853F',
      secondary: '#FDEF42',
      text: '#F8FFF2',
    },
  },
  {
    id: 'world-cup-iraq',
    name: 'Iraque',
    mode: 'light',
    category: 'world-cup',
    continent: 'AFC',
    description: 'Branco com vermelho, preto e verde iraquianos',
    preview: { colors: ['#FFFFFF', '#CE1126', '#000000', '#007A3D'], pattern: 'bands' },
    colors: {
      surface: '#F8FAF8',
      card: '#FFFFFF',
      primary: '#CE1126',
      secondary: '#007A3D',
      text: '#171717',
    },
  },
  {
    id: 'world-cup-algeria',
    name: 'Argelia',
    mode: 'light',
    category: 'world-cup',
    continent: 'CAF',
    description: 'Verde e branco limpos com detalhe vermelho',
    preview: { colors: ['#006233', '#FFFFFF', '#D21034'], pattern: 'bands' },
    colors: {
      surface: '#F0FFF6',
      card: '#FFFFFF',
      primary: '#006233',
      secondary: '#D21034',
      text: '#10261A',
    },
  },
  {
    id: 'world-cup-austria',
    name: 'Austria',
    mode: 'light',
    category: 'world-cup',
    continent: 'UEFA',
    description: 'Vermelho e branco classicos da bandeira austriaca',
    preview: { colors: ['#ED2939', '#FFFFFF', '#C8102E'], pattern: 'stripes' },
    colors: {
      surface: '#FFF2F3',
      card: '#FFFFFF',
      primary: '#ED2939',
      secondary: '#FFFFFF',
      text: '#241315',
    },
  },
  {
    id: 'world-cup-jordan',
    name: 'Jordania',
    mode: 'dark',
    category: 'world-cup',
    continent: 'AFC',
    description: 'Vermelho, preto, branco e verde da bandeira jordaniana',
    preview: { colors: ['#CE1126', '#000000', '#FFFFFF', '#007A3D'], pattern: 'bands' },
    colors: {
      surface: '#151515',
      card: '#242424',
      primary: '#CE1126',
      secondary: '#007A3D',
      text: '#F8FAFC',
    },
  },
  {
    id: 'world-cup-jamaica',
    name: 'Jamaica',
    mode: 'dark',
    category: 'world-cup',
    continent: 'CONCACAF',
    description: 'Dourado vibrante com verde e preto jamaicanos',
    preview: { colors: ['#FED100', '#009B3A', '#000000'], pattern: 'cross' },
    colors: {
      surface: '#0E170C',
      card: '#182414',
      primary: '#FED100',
      secondary: '#009B3A',
      text: '#FFFBEA',
    },
  },
  {
    id: 'world-cup-uzbekistan',
    name: 'Uzbequistao',
    mode: 'light',
    category: 'world-cup',
    continent: 'AFC',
    description: 'Azul claro com branco, verde e vermelho',
    preview: { colors: ['#0099B5', '#FFFFFF', '#1EB53A', '#CE1126'], pattern: 'stripes' },
    colors: {
      surface: '#EAFBFF',
      card: '#FFFFFF',
      primary: '#0099B5',
      secondary: '#1EB53A',
      text: '#10252A',
    },
  },
  {
    id: 'world-cup-ghana',
    name: 'Gana',
    mode: 'dark',
    category: 'world-cup',
    continent: 'CAF',
    description: 'Vermelho, dourado, verde e preto fortes',
    preview: { colors: ['#CE1126', '#FCD116', '#006B3F', '#000000'], pattern: 'bands' },
    colors: {
      surface: '#1F0D0E',
      card: '#2E1714',
      primary: '#CE1126',
      secondary: '#FCD116',
      text: '#FFF8E6',
    },
  },
  {
    id: 'world-cup-panama',
    name: 'Panama',
    mode: 'light',
    category: 'world-cup',
    continent: 'CONCACAF',
    description: 'Base branca com destaques vermelho e azul',
    preview: { colors: ['#FFFFFF', '#D21034', '#005293'], pattern: 'checker' },
    colors: {
      surface: '#F7FAFF',
      card: '#FFFFFF',
      primary: '#005293',
      secondary: '#D21034',
      text: '#151B2A',
    },
  },
]

export const THEME_OPTIONS: ThemeOption[] = [
  ...CLASSIC_THEME_OPTIONS,
  ...WORLD_CUP_THEME_OPTIONS,
]

const STORAGE_KEY = 'saltim-appearance-theme'
const DEFAULT_THEME = 'maestro-light'
const RUNTIME_WORLD_CUP_PROPERTIES = [
  '--cup-surface',
  '--cup-card',
  '--cup-sidebar',
  '--cup-logo',
  '--cup-primary',
  '--cup-secondary',
  '--cup-accent',
  '--cup-red',
  '--cup-green',
  '--cup-blue',
  '--theme-on-primary',
  '--theme-stone-50',
  '--theme-stone-100',
  '--theme-stone-200',
  '--theme-stone-300',
  '--theme-stone-400',
  '--theme-stone-500',
  '--theme-stone-600',
  '--theme-stone-700',
  '--theme-stone-800',
  '--theme-stone-900',
  '--theme-stone-950',
]

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

function isLightHexColor(hexColor: string) {
  const hex = hexColor.replace('#', '')
  if (hex.length !== 6) return false
  const red = parseInt(hex.slice(0, 2), 16)
  const green = parseInt(hex.slice(2, 4), 16)
  const blue = parseInt(hex.slice(4, 6), 16)
  return (red * 299 + green * 587 + blue * 114) / 1000 > 155
}

function applyRuntimeWorldCupTheme(root: HTMLElement, theme: ThemeOption) {
  const shouldApplyRuntimeCupTheme = theme.category === 'world-cup' && Boolean(theme.continent)
  if (!shouldApplyRuntimeCupTheme) {
    RUNTIME_WORLD_CUP_PROPERTIES.forEach((property) => root.style.removeProperty(property))
    return
  }

  const previewColors = theme.preview?.colors ?? [
    theme.colors.primary,
    theme.colors.secondary,
    theme.colors.card,
  ]
  const accent = previewColors[2] ?? theme.colors.card
  const support = previewColors[3] ?? theme.colors.secondary

  root.style.setProperty('--cup-surface', theme.colors.surface)
  root.style.setProperty('--cup-card', theme.colors.card)
  root.style.setProperty('--cup-sidebar', theme.mode === 'dark' ? theme.colors.surface : theme.colors.primary)
  root.style.setProperty('--cup-logo', theme.colors.secondary)
  root.style.setProperty('--cup-primary', theme.colors.primary)
  root.style.setProperty('--cup-secondary', theme.colors.secondary)
  root.style.setProperty('--cup-accent', accent)
  root.style.setProperty('--cup-red', accent)
  root.style.setProperty('--cup-green', theme.colors.secondary)
  root.style.setProperty('--cup-blue', support)
  root.style.setProperty('--theme-on-primary', isLightHexColor(theme.colors.primary) ? '#18181B' : '#FFFFFF')

  const lightScale = {
    '--theme-stone-50': '#FAFAFA',
    '--theme-stone-100': '#F4F4F5',
    '--theme-stone-200': '#E4E4E7',
    '--theme-stone-300': '#D4D4D8',
    '--theme-stone-400': '#A1A1AA',
    '--theme-stone-500': '#71717A',
    '--theme-stone-600': '#52525B',
    '--theme-stone-700': '#3F3F46',
    '--theme-stone-800': '#27272A',
    '--theme-stone-900': '#18181B',
    '--theme-stone-950': '#09090B',
  }
  const darkScale = {
    '--theme-stone-50': theme.colors.card,
    '--theme-stone-100': `color-mix(in srgb, ${theme.colors.card} 86%, white)`,
    '--theme-stone-200': `color-mix(in srgb, ${theme.colors.card} 70%, white)`,
    '--theme-stone-300': `color-mix(in srgb, ${theme.colors.card} 52%, white)`,
    '--theme-stone-400': `color-mix(in srgb, ${theme.colors.card} 34%, white)`,
    '--theme-stone-500': `color-mix(in srgb, ${theme.colors.card} 16%, white)`,
    '--theme-stone-600': '#E4E4E7',
    '--theme-stone-700': '#F4F4F5',
    '--theme-stone-800': '#FAFAFA',
    '--theme-stone-900': '#FFFFFF',
    '--theme-stone-950': '#FFFFFF',
  }
  const scale = theme.mode === 'light' ? lightScale : darkScale
  Object.entries(scale).forEach(([property, value]) => root.style.setProperty(property, value))
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
    applyRuntimeWorldCupTheme(root, theme)
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
