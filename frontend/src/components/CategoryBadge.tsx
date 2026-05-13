import type { Category } from '../data/ingredients'

const COLORS: Record<Category, { bg: string; text: string }> = {
  'Laticínios':                { bg: '#f0f9ff', text: '#0369a1' },
  'Proteínas':                 { bg: '#fff1f2', text: '#be123c' },
  'Grãos, Farinhas e Massas':  { bg: '#fffbeb', text: '#b45309' },
  'Açúcares e Mel':            { bg: '#fefce8', text: '#854d0e' },
  'Chocolates e Cacau':        { bg: '#fef3c7', text: '#78350f' },
  'Nozes e Sementes':          { bg: '#fff7ed', text: '#c2410c' },
  'Frutas Frescas':            { bg: '#f0fdf4', text: '#15803d' },
  'Frutas Secas e Congeladas': { bg: '#faf5ff', text: '#7e22ce' },
  'Legumes e Verduras':        { bg: '#ecfdf5', text: '#047857' },
  'Temperos e Especiarias':    { bg: '#f0fdfa', text: '#0f766e' },
  'Óleos e Gorduras':          { bg: '#f7fee7', text: '#4d7c0f' },
  'Molhos e Condimentos':      { bg: '#eef2ff', text: '#3730a3' },
  'Bebidas e Bases':           { bg: '#ecfeff', text: '#0e7490' },
  'Semi-prontos e Preparados': { bg: '#f8fafc', text: '#475569' },
}

interface Props {
  category: Category
  className?: string
}

export function CategoryBadge({ category, className = '' }: Props) {
  const { bg, text } = COLORS[category]
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${className}`}
      style={{ backgroundColor: bg, color: text }}
    >
      {category}
    </span>
  )
}

export { COLORS as CATEGORY_COLORS }
