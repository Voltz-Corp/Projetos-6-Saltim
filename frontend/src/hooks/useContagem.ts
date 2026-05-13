import { useState } from 'react'
import type { StockItem } from './useEstoque'

// Module-level state persists across category route changes
const globalCounts = new Map<number, number>()
const globalTouched = new Set<number>()

export function resetContagem() {
  globalCounts.clear()
  globalTouched.clear()
}

// Pré-inicializa todos os itens: preenche contagens e marca os que já atingem o mínimo.
// Idempotente — seguro chamar em qualquer render.
export function initializeAll(allItems: StockItem[]) {
  for (const item of allItems) {
    if (!globalCounts.has(item.id)) {
      globalCounts.set(item.id, item.currentQty)
      if (item.currentQty >= item.minQty) {
        globalTouched.add(item.id)
      }
    }
  }
}

export function getGlobalProgress(allItems: StockItem[]) {
  const touchedCount = allItems.filter(i => globalTouched.has(i.id)).length
  const totalCount = allItems.length
  return {
    touchedCount,
    totalCount,
    progress: totalCount === 0 ? 0 : touchedCount / totalCount,
  }
}

export function isCategoryComplete(items: StockItem[]) {
  return items.length > 0 && items.every(i => globalTouched.has(i.id))
}

export function buildAllUpdates(allItems: StockItem[]): Map<number, number> {
  const updates = new Map<number, number>()
  for (const item of allItems) {
    if (globalTouched.has(item.id)) {
      updates.set(item.id, globalCounts.get(item.id) ?? 0)
    }
  }
  return updates
}

export function useContagem(items: StockItem[]) {
  const [, forceRender] = useState(0)

  // Pré-preenche com o estoque atual na primeira vez que o item aparece.
  // Itens acima do mínimo são marcados automaticamente como contados.
  for (const item of items) {
    if (!globalCounts.has(item.id)) {
      globalCounts.set(item.id, item.currentQty)
      if (item.currentQty >= item.minQty) {
        globalTouched.add(item.id)
      }
    }
  }

  function commit(id: number, next: number) {
    globalCounts.set(id, next)
    if (next === 0) globalTouched.delete(id)
    else globalTouched.add(id)
    forceRender(n => n + 1)
  }

  function adjust(id: number, delta: number) {
    const cur = globalCounts.get(id) ?? 0
    // Round to 3 decimal places to avoid floating-point drift (0.1 + 0.1 + 0.1 ≠ 0.3)
    commit(id, Math.max(0, Math.round((cur + delta) * 1000) / 1000))
  }

  function setCount(id: number, value: number) {
    commit(id, Math.max(0, Math.round(value * 1000) / 1000))
  }

  // Marca como contado sem alterar o valor — útil quando o estoque atual já está correto.
  function confirmar(id: number) {
    globalTouched.add(id)
    forceRender(n => n + 1)
  }

  // Remove a marcação de contado (volta ao estado pendente).
  function desmarcar(id: number) {
    globalTouched.delete(id)
    forceRender(n => n + 1)
  }

  function getCount(id: number) {
    return globalCounts.get(id) ?? 0
  }

  function isTouched(id: number) {
    return globalTouched.has(id)
  }

  function marcarTodos() {
    for (const item of items) {
      globalTouched.add(item.id)
    }
    forceRender(n => n + 1)
  }

  const touchedCount = items.filter(i => globalTouched.has(i.id)).length
  const totalCount = items.length
  const progress = totalCount === 0 ? 0 : touchedCount / totalCount

  function buildUpdates(): Map<number, number> {
    const updates = new Map<number, number>()
    for (const item of items) {
      if (globalTouched.has(item.id)) {
        updates.set(item.id, globalCounts.get(item.id) ?? 0)
      }
    }
    return updates
  }

  return { adjust, setCount, confirmar, desmarcar, marcarTodos, getCount, isTouched, progress, touchedCount, totalCount, buildUpdates }
}
