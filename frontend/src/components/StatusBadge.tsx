import { getStockStatus, type StockItem, type StockStatus } from '../hooks/useEstoque'

// Paleta Saltim: verde logo, laranja logo, vermelho logo, fundo escuro logo
const CONFIG: Record<StockStatus, { bg: string; text: string; dot: string }> = {
  'OK':       { bg: '#edf6ee', text: '#2D7A3A', dot: '#2D7A3A' },
  'Atenção':  { bg: '#FEF4E8', text: '#C5621A', dot: '#F07820' },
  'Crítico':  { bg: '#fdecea', text: '#E4332B', dot: '#E4332B' },
  'Esgotado': { bg: '#1A1918', text: '#EDE0B4', dot: '#EDE0B4' },
}

interface Props {
  item: StockItem
}

export function StatusBadge({ item }: Props) {
  const status = getStockStatus(item)
  const { bg, text, dot } = CONFIG[status]
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium whitespace-nowrap"
      style={{ backgroundColor: bg, color: text }}
    >
      <span className="size-1.5 rounded-full flex-shrink-0" style={{ backgroundColor: dot }} />
      {status}
    </span>
  )
}
