import { useState, useEffect } from 'react'
import { createRoute, useNavigate } from '@tanstack/react-router'
import { rootRoute } from './Root'
import { useEstoque, useAtualizarIngrediente } from '../hooks/useEstoque'
import { CATEGORIES } from '../data/ingredients'

export const ingredienteEditRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/ingredientes/$id/editar',
  component: IngredienteEditPage,
})

export function IngredienteEditPage() {
  const navigate = useNavigate()
  const { id } = ingredienteEditRoute.useParams()
  const { data: stock = [] } = useEstoque()
  const atualizar = useAtualizarIngrediente()

  const item = stock.find(i => i.id === Number(id))

  const [name, setName] = useState('')
  const [unit, setUnit] = useState('')
  const [price, setPrice] = useState('')
  const [category, setCategory] = useState('')
  const [minQty, setMinQty] = useState('')

  useEffect(() => {
    if (item) {
      setName(item.name)
      setUnit(item.unit)
      setPrice(String(item.price))
      setCategory(item.category)
      setMinQty(String(item.min_qty))
    }
  }, [item?.id])

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    if (!item) return
    await atualizar.mutateAsync({
      id: item.id,
      name: name.trim() || undefined,
      unit: unit.trim() || undefined,
      price: price !== '' ? parseFloat(price) : undefined,
      category: category || undefined,
      min_qty: minQty !== '' ? parseFloat(minQty) : undefined,
    })
    navigate({ to: '/estoque' })
  }

  if (!item) {
    return (
      <div className="flex flex-col h-screen bg-surface items-center justify-center">
        <p className="text-stone-400 text-sm">Ingrediente não encontrado.</p>
      </div>
    )
  }

  const inputClass = 'w-full px-3 py-2 text-sm border border-stone-200 rounded-lg bg-white outline-none focus:ring-2 focus:ring-brand-600/20 focus:border-brand-600 transition'
  const labelClass = 'block text-xs font-medium text-stone-500 mb-1'

  return (
    <div className="flex flex-col h-screen bg-surface">
      {/* Header */}
      <div className="bg-white border-b border-stone-200 px-8 py-4 flex items-center gap-3 flex-shrink-0">
        <button
          type="button"
          onClick={() => navigate({ to: '/estoque' })}
          className="size-8 rounded-lg border border-stone-200 flex items-center justify-center hover:bg-stone-50 transition-colors cursor-pointer flex-shrink-0"
        >
          <svg viewBox="0 0 20 20" className="size-4 text-stone-400" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="12 4 4 10 12 16" />
          </svg>
        </button>
        <div className="flex-1 min-w-0">
          <p className="text-xs text-stone-400 font-medium uppercase tracking-wide">Editar ingrediente</p>
          <h1 className="text-lg font-semibold text-stone-900 leading-tight truncate">{item.name}</h1>
        </div>
      </div>

      {/* Form */}
      <div className="flex-1 overflow-auto p-8">
        <form onSubmit={handleSave} className="max-w-lg mx-auto flex flex-col gap-5">

          <div>
            <label className={labelClass}>Nome</label>
            <input
              value={name}
              onChange={e => setName(e.target.value)}
              required
              className={inputClass}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelClass}>Unidade</label>
              <input
                value={unit}
                onChange={e => setUnit(e.target.value)}
                required
                placeholder="ex: UND, KG, L"
                className={inputClass}
              />
            </div>
            <div>
              <label className={labelClass}>Preço / unidade (R$)</label>
              <input
                type="number"
                min="0"
                step="0.01"
                value={price}
                onChange={e => setPrice(e.target.value)}
                required
                className={inputClass}
              />
            </div>
          </div>

          <div>
            <label className={labelClass}>Categoria</label>
            <select
              value={category}
              onChange={e => setCategory(e.target.value)}
              required
              className={inputClass}
            >
              {CATEGORIES.map(cat => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>
          </div>

          <div>
            <label className={labelClass}>Quantidade mínima</label>
            <input
              type="number"
              min="0"
              step="0.001"
              value={minQty}
              onChange={e => setMinQty(e.target.value)}
              required
              className={inputClass}
            />
          </div>

          <div className="pt-2 flex gap-3">
            <button
              type="button"
              onClick={() => navigate({ to: '/estoque' })}
              className="flex-1 py-2.5 rounded-xl text-sm font-semibold border border-stone-200 bg-white text-stone-600 hover:bg-stone-50 transition-colors cursor-pointer"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={atualizar.isPending}
              className="flex-1 py-2.5 rounded-xl text-sm font-semibold bg-brand-600 text-white hover:bg-brand-700 transition-colors disabled:opacity-60 cursor-pointer"
            >
              {atualizar.isPending ? 'Salvando…' : 'Salvar'}
            </button>
          </div>

          {atualizar.isError && (
            <p className="text-sm text-red-600 text-center">Erro ao salvar. Tente novamente.</p>
          )}
        </form>
      </div>
    </div>
  )
}
