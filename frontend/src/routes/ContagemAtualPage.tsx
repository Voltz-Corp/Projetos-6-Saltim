import { useEffect, useState } from 'react'
import { createRoute, useNavigate } from '@tanstack/react-router'
import { rootRoute } from './Root'
import { useEstoque, getStockStatus } from '../hooks/useEstoque'
import { CATEGORIES, type Category } from '../data/ingredients'
import { fetchContagemDetalhe } from '../hooks/useContagens'
import {
  getGlobalProgress,
  hydrateContagemSession,
  isCategoryComplete,
  initializeAll,
  useContagemSession,
} from '../hooks/useContagem'
import { cn } from '../lib/cn'

export const contagemAtualRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/estoque/contagem/atual',
  component: ContagemAtualPage,
})

export function ContagemAtualPage() {
  const navigate = useNavigate()
  const { data: stock = [] } = useEstoque()
  const contagem = useContagemSession()
  const [, forceRender] = useState(0)

  useEffect(() => {
    let active = true
    async function loadContagemHoje() {
      const contagemId = await contagem.ensure()
      const detalhe = await fetchContagemDetalhe(contagemId)
      if (active) {
        hydrateContagemSession(detalhe, detalhe.categorias.flatMap((categoria) => categoria.items))
        forceRender((value) => value + 1)
      }
    }
    loadContagemHoje()
    return () => {
      active = false
    }
  }, [])

  initializeAll(stock)

  const globalProgress = getGlobalProgress(stock)
  const pct = Math.round(globalProgress.progress * 100)

  function critical(cat: Category) {
    return stock.filter(i => i.category === cat && getStockStatus(i) === 'Crítico').length
  }

  function itemCount(cat: Category) {
    return stock.filter(i => i.category === cat).length
  }

  return (
    <div className="flex flex-col h-screen bg-surface">
      <div className="flex h-[73px] flex-shrink-0 items-center gap-3 border-b border-stone-200 bg-white px-8">
        <button
          onClick={() => navigate({ to: '/estoque/contagem' })}
          className="size-8 rounded-lg border border-stone-200 flex items-center justify-center hover:bg-stone-50 transition-colors cursor-pointer flex-shrink-0"
        >
          <svg viewBox="0 0 20 20" className="size-4 text-stone-400" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="12 4 4 10 12 16" />
          </svg>
        </button>
        <div className="flex-1">
          <h1 className="text-xl font-semibold text-stone-900">Contagem de hoje</h1>
          <p className="text-xs text-stone-400 mt-0.5">
            {contagem.label || 'Criando contagem...'} · selecione a categoria para começar
          </p>
        </div>
      </div>

      <div className="px-8 pt-5 pb-2 flex-shrink-0">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium text-stone-500">Progresso da contagem</span>
          <span className="text-xs tabular-nums text-stone-500">
            <span className="font-bold text-stone-900">{globalProgress.touchedCount}</span>
            {' / '}{globalProgress.totalCount} itens
          </span>
        </div>
        <div className="h-1.5 bg-white border border-stone-200 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{ width: `${pct}%`, backgroundColor: pct === 100 ? '#2D7A3A' : '#F07820' }}
          />
        </div>
      </div>

      <div className="flex-1 overflow-auto px-8 pb-8 pt-4">
        <div className="grid grid-cols-2 gap-3">
          {CATEGORIES.map((cat, idx) => {
            const crit = critical(cat)
            const count = itemCount(cat)
            const catItems = stock.filter(i => i.category === cat)
            const done = isCategoryComplete(catItems)
            return (
              <button
                key={cat}
                onClick={() => navigate({ to: '/estoque/contagem/atual/$index', params: { index: String(idx) } })}
                className={cn(
                  'border rounded-xl px-5 py-4 flex items-start justify-between text-left transition-all hover:shadow-sm cursor-pointer',
                  done
                    ? 'border-green-300 bg-green-50 hover:border-green-400'
                    : 'bg-white border-stone-200 hover:border-stone-300',
                )}
              >
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-semibold text-stone-900">{cat}</div>
                  <div className="text-xs text-stone-400 mt-0.5">{count} insumos</div>
                </div>
                <div className="flex-shrink-0 ml-3 mt-0.5">
                  {done ? (
                    <span className="inline-flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-full bg-green-100 text-green-700">
                      <svg viewBox="0 0 20 20" className="size-3" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="4 10 8 14 16 6" />
                      </svg>
                      Contada
                    </span>
                  ) : crit > 0 ? (
                    <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-red-50 text-red-700">
                      {crit} crítico{crit > 1 ? 's' : ''}
                    </span>
                  ) : (
                    <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-stone-100 text-stone-600">
                      Não contada
                    </span>
                  )}
                </div>
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
