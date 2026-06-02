import { useMemo, useState } from 'react'
import { createRoute, useNavigate } from '@tanstack/react-router'
import { ArrowLeft, ChevronDown, Plus, Search, Trash2 } from 'lucide-react'
import { rootRoute } from './Root'
import { useCreateFornecedor } from '../hooks/useFornecedores'
import { useEstoque, type StockItem } from '../hooks/useEstoque'

export const fornecedorNewRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/fornecedores/novo',
  component: FornecedorNewPage,
})

interface SelectedIngredient {
  ingredient: StockItem
  price: string
}

function FornecedorNewPage() {
  const navigate = useNavigate()
  const createFornecedor = useCreateFornecedor()
  const { data: ingredients = [] } = useEstoque()

  const [name, setName] = useState('')
  const [cnpj, setCnpj] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [avgDeliveryTime, setAvgDeliveryTime] = useState('')
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<SelectedIngredient[]>([])
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set())

  const selectedIds = useMemo(
    () => new Set(selected.map((item) => String(item.ingredient.id))),
    [selected],
  )
  const available = useMemo(
    () =>
      ingredients.filter(
        (ingredient) =>
          !selectedIds.has(String(ingredient.id)) &&
          ingredient.name.toLowerCase().includes(search.toLowerCase()),
      ),
    [ingredients, search, selectedIds],
  )
  const groupedAvailable = useMemo(() => {
    const groups = new Map<string, StockItem[]>()
    available.forEach((ingredient) => {
      const category = ingredient.category || 'Sem categoria'
      groups.set(category, [...(groups.get(category) ?? []), ingredient])
    })
    return Array.from(groups.entries()).sort(([a], [b]) => a.localeCompare(b))
  }, [available])

  function addIngredient(ingredient: StockItem) {
    setSelected((current) => [
      ...current,
      { ingredient, price: ingredient.price ? String(ingredient.price) : '' },
    ])
  }

  function removeIngredient(id: string | number) {
    setSelected((current) =>
      current.filter((item) => String(item.ingredient.id) !== String(id)),
    )
  }

  function updatePrice(id: string | number, price: string) {
    setSelected((current) =>
      current.map((item) =>
        String(item.ingredient.id) === String(id) ? { ...item, price } : item,
      ),
    )
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    await createFornecedor.mutateAsync({
      name,
      cnpj: onlyDigits(cnpj) || undefined,
      email: email || undefined,
      phone: onlyDigits(phone) || undefined,
      avg_delivery_time: avgDeliveryTime ? Number(avgDeliveryTime) : undefined,
      ingredients: selected.map((item) => ({
        ingredient_id: String(item.ingredient.id),
        price: Number(item.price || 0),
      })),
    })
    navigate({ to: '/fornecedores' })
  }

  const canSubmit =
    name.trim().length > 0 &&
    (!cnpj || isValidCnpj(cnpj)) &&
    (!phone || isValidPhone(phone)) &&
    selected.length > 0 &&
    selected.every((item) => Number(item.price) > 0)

  function toggleCategory(category: string) {
    setExpandedCategories((current) => {
      const next = new Set(current)
      if (next.has(category)) next.delete(category)
      else next.add(category)
      return next
    })
  }

  return (
    <div className="flex h-screen flex-col bg-surface">
      <header className="flex flex-shrink-0 items-center gap-3 border-b border-stone-200 bg-white px-8 py-4">
        <button
          type="button"
          onClick={() => navigate({ to: '/fornecedores' })}
          className="flex size-9 items-center justify-center rounded-lg border border-stone-200 text-stone-500 transition hover:bg-stone-50 hover:text-stone-900"
          aria-label="Voltar"
        >
          <ArrowLeft className="size-4" strokeWidth={2} />
        </button>
        <div>
          <p className="text-xs font-bold uppercase tracking-wide text-brand-600">
            Novo fornecedor
          </p>
          <h1 className="text-xl font-semibold text-stone-900">
            Cadastro de fornecedor
          </h1>
        </div>
      </header>

      <main className="flex-1 overflow-auto p-6">
        <form onSubmit={handleSubmit} className="space-y-6">
          <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
            <h2 className="text-sm font-black text-stone-900">
              Dados do fornecedor
            </h2>
            <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
              <Field label="Nome">
                <input value={name} onChange={(event) => setName(event.target.value)} required className={inputClass} />
              </Field>
              <Field label="CNPJ">
                <input
                  value={cnpj}
                  onChange={(event) => setCnpj(maskCnpj(event.target.value))}
                  className={inputClass}
                  inputMode="numeric"
                  placeholder="00.000.000/0000-00"
                  pattern="\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}"
                />
              </Field>
              <Field label="Email">
                <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} className={inputClass} />
              </Field>
              <Field label="Telefone">
                <input
                  value={phone}
                  onChange={(event) => setPhone(maskPhone(event.target.value))}
                  className={inputClass}
                  inputMode="numeric"
                  placeholder="(00) 00000-0000"
                  pattern="\(\d{2}\) \d{4,5}-\d{4}"
                />
              </Field>
              <Field label="Prazo médio">
                <input type="number" min="0" value={avgDeliveryTime} onChange={(event) => setAvgDeliveryTime(event.target.value)} className={inputClass} placeholder="dias" />
              </Field>
            </div>
          </section>

          <section className="grid grid-cols-1 gap-6 xl:grid-cols-2">
            <IngredientList
              title="Ingredientes disponíveis"
              subtitle="Selecione os ingredientes vendidos por este fornecedor"
              search={search}
              onSearchChange={setSearch}
            >
              {groupedAvailable.length === 0 ? (
                <div className="px-4 py-16 text-center text-sm text-stone-400">
                  Nenhum ingrediente encontrado.
                </div>
              ) : (
                groupedAvailable.map(([category, items]) => {
                  const expanded = expandedCategories.has(category)
                  return (
                    <section key={category} className="border-b border-stone-100 last:border-0">
                      <button
                        type="button"
                        onClick={() => toggleCategory(category)}
                        className="flex w-full items-center justify-between gap-3 bg-stone-50/70 px-4 py-3 text-left transition hover:bg-stone-100"
                      >
                        <span>
                          <span className="block text-xs font-black uppercase tracking-wide text-stone-700">
                            {category}
                          </span>
                          <span className="text-[11px] font-medium text-stone-400">
                            {items.length} ingrediente{items.length !== 1 ? 's' : ''}
                          </span>
                        </span>
                        <ChevronDown
                          className={[
                            'size-4 text-stone-400 transition-transform',
                            expanded ? 'rotate-180' : '',
                          ].join(' ')}
                          strokeWidth={2}
                        />
                      </button>
                      {expanded && items.map((ingredient) => (
                        <button
                          key={ingredient.id}
                          type="button"
                          onClick={() => addIngredient(ingredient)}
                          className="flex w-full items-center justify-between gap-3 border-t border-stone-100 px-4 py-3 text-left transition hover:bg-stone-50"
                        >
                          <div className="min-w-0">
                            <p className="truncate text-sm font-bold text-stone-900">
                              {ingredient.name}
                            </p>
                            <p className="text-xs text-stone-400">
                              {ingredient.category} · {ingredient.unit}
                            </p>
                          </div>
                          <Plus className="size-4 flex-shrink-0 text-brand-600" />
                        </button>
                      ))}
                    </section>
                  )
                })
              )}
            </IngredientList>

            <IngredientList
              title="Lista do fornecedor"
              subtitle={`${selected.length} ingrediente${selected.length !== 1 ? 's' : ''} selecionado${selected.length !== 1 ? 's' : ''}`}
            >
              {selected.length === 0 ? (
                <div className="px-4 py-16 text-center text-sm text-stone-400">
                  Nenhum ingrediente selecionado.
                </div>
              ) : (
                selected.map(({ ingredient, price }) => (
                  <div
                    key={ingredient.id}
                    className="grid grid-cols-[minmax(0,1fr)_120px_36px] items-center gap-3 border-b border-stone-100 px-4 py-3 last:border-0"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-bold text-stone-900">
                        {ingredient.name}
                      </p>
                      <p className="text-xs text-stone-400">
                        {ingredient.category} · {ingredient.unit}
                      </p>
                    </div>
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={price}
                      onChange={(event) => updatePrice(ingredient.id, event.target.value)}
                      className={inputClass}
                      placeholder="Preço"
                    />
                    <button
                      type="button"
                      onClick={() => removeIngredient(ingredient.id)}
                      className="flex size-9 items-center justify-center rounded-lg text-stone-400 transition hover:bg-red-50 hover:text-red-600"
                      aria-label="Remover ingrediente"
                    >
                      <Trash2 className="size-4" strokeWidth={2} />
                    </button>
                  </div>
                ))
              )}
            </IngredientList>
          </section>

          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={() => navigate({ to: '/fornecedores' })}
              className="rounded-lg border border-stone-200 px-4 py-2 text-sm font-bold text-stone-600 transition hover:bg-stone-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={!canSubmit || createFornecedor.isPending}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-bold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {createFornecedor.isPending ? 'Salvando...' : 'Salvar fornecedor'}
            </button>
          </div>
        </form>
      </main>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="grid gap-1">
      <span className="text-[11px] font-black uppercase tracking-wide text-stone-400">
        {label}
      </span>
      {children}
    </label>
  )
}

function IngredientList({
  title,
  subtitle,
  search,
  onSearchChange,
  children,
}: {
  title: string
  subtitle: string
  search?: string
  onSearchChange?: (value: string) => void
  children: React.ReactNode
}) {
  return (
    <section className="overflow-hidden rounded-xl border border-stone-200 bg-white shadow-sm">
      <div className="border-b border-stone-100 p-5">
        <h2 className="text-sm font-black text-stone-900">{title}</h2>
        <p className="mt-1 text-xs text-stone-400">{subtitle}</p>
        {onSearchChange && (
          <div className="relative mt-4">
            <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-stone-400" />
            <input
              value={search}
              onChange={(event) => onSearchChange(event.target.value)}
              className={`${inputClass} pl-9`}
              placeholder="Buscar ingrediente"
            />
          </div>
        )}
      </div>
      <div className="max-h-[520px] overflow-auto">{children}</div>
    </section>
  )
}

const inputClass =
  'h-9 w-full rounded-lg border border-stone-200 bg-white px-3 text-sm text-stone-700 outline-none transition focus:border-brand-600 focus:ring-2 focus:ring-brand-600/20'

function onlyDigits(value: string) {
  return value.replace(/\D/g, '')
}

function maskCnpj(value: string) {
  const digits = onlyDigits(value).slice(0, 14)
  return digits
    .replace(/^(\d{2})(\d)/, '$1.$2')
    .replace(/^(\d{2})\.(\d{3})(\d)/, '$1.$2.$3')
    .replace(/\.(\d{3})(\d)/, '.$1/$2')
    .replace(/(\d{4})(\d)/, '$1-$2')
}

function maskPhone(value: string) {
  const digits = onlyDigits(value).slice(0, 11)
  if (digits.length <= 10) {
    return digits
      .replace(/^(\d{2})(\d)/, '($1) $2')
      .replace(/(\d{4})(\d)/, '$1-$2')
  }
  return digits
    .replace(/^(\d{2})(\d)/, '($1) $2')
    .replace(/(\d{5})(\d)/, '$1-$2')
}

function isValidCnpj(value: string) {
  return onlyDigits(value).length === 14
}

function isValidPhone(value: string) {
  return [10, 11].includes(onlyDigits(value).length)
}
