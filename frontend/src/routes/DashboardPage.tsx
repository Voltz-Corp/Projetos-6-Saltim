import { useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { createRoute } from '@tanstack/react-router'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { rootRoute } from './Root'
import {
  useDashboard,
  useRecipeRanking,
  useSalesHistory,
  useStockHistory,
  type DashboardAlert,
  type DashboardCategoryItem,
  type DashboardRankItem,
  type DashboardUnitCategoryGroup,
  type DashboardUnitRankGroup,
  type StockHistoryPoint,
} from '../hooks/useDashboard'

export const dashboardRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  component: DashboardPage,
})

const fmt = {
  number: (value: number, maximumFractionDigits = 1) =>
    value.toLocaleString('pt-BR', { maximumFractionDigits }),
  compact: (value: number) =>
    Intl.NumberFormat('pt-BR', {
      notation: 'compact',
      maximumFractionDigits: 1,
    }).format(value),
  currency: (value: number) =>
    value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }),
  date: (value: string) =>
    new Date(`${value}T00:00:00`).toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
    }),
}

function shortLabel(value: string, max = 20) {
  return value.length > max ? `${value.slice(0, max - 1)}...` : value
}

function itemWithUnit(item?: { name: string; value: number; unit?: string | null }) {
  if (!item) return '-'
  return `${item.unit ?? ''}: ${item.name}`
}

function unitDetail(items: Array<{ value: number; unit?: string | null }>) {
  if (!items.length) return '-'
  return items.map(item => `${fmt.number(item.value, 2)} ${item.unit ?? ''}`).join(' · ')
}

function StatCard({
  label,
  value,
  detail,
  tone = 'ink',
}: {
  label: string
  value: string
  detail?: string
  tone?: 'ink' | 'green' | 'orange' | 'red' | 'blue'
}) {
  const color = {
    ink: 'text-stone-900',
    green: 'text-saltim-green',
    orange: 'text-saltim-orange',
    red: 'text-saltim-red',
    blue: 'text-saltim-blue',
  }[tone]

  return (
    <div className="bg-white rounded-xl border border-stone-200 p-5 min-w-0">
      <div className="text-xs font-semibold text-stone-400 uppercase tracking-wide">{label}</div>
      <div className={`mt-3 text-xl font-bold tabular-nums leading-snug break-words ${color}`}>
        {value}
      </div>
      {detail && <div className="mt-2 text-sm text-stone-500 break-words">{detail}</div>}
    </div>
  )
}

function Panel({
  title,
  children,
  action,
}: {
  title: string
  children: ReactNode
  action?: ReactNode
}) {
  return (
    <section className="bg-white rounded-xl border border-stone-200 min-w-0 overflow-hidden">
      <div className="px-5 py-4 border-b border-stone-100 flex flex-col gap-3 lg:flex-row lg:items-center">
        <h2 className="text-sm font-semibold text-stone-900 flex-1 min-w-0">{title}</h2>
        {action}
      </div>
      <div className="p-4">{children}</div>
    </section>
  )
}

function EmptyState() {
  return (
    <div className="h-56 flex items-center justify-center text-sm text-stone-400">
      Sem dados para exibir
    </div>
  )
}

function UnitFilters({
  categoryId,
  ingredientId,
  days,
  categories,
  ingredients,
  onCategoryChange,
  onIngredientChange,
  onDaysChange,
}: {
  categoryId: string
  ingredientId: string
  days: number
  categories: DashboardCategoryItem[]
  ingredients: Array<{ id: string; name: string; category_id: string }>
  onCategoryChange: (value: string) => void
  onIngredientChange: (value: string) => void
  onDaysChange: (value: number) => void
}) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <select
        value={categoryId}
        onChange={event => onCategoryChange(event.target.value)}
        className="h-9 max-w-48 rounded-lg border border-stone-200 bg-white px-3 text-sm text-stone-700 outline-none focus:border-brand-600 focus:ring-2 focus:ring-brand-600/20"
      >
        <option value="">Todas as categorias</option>
        {categories.map(category => (
          <option key={category.id} value={category.id}>
            {category.name}
          </option>
        ))}
      </select>
      <select
        value={ingredientId}
        onChange={event => onIngredientChange(event.target.value)}
        className="h-9 max-w-56 rounded-lg border border-stone-200 bg-white px-3 text-sm text-stone-700 outline-none focus:border-brand-600 focus:ring-2 focus:ring-brand-600/20"
      >
        <option value="">Todos os ingredientes</option>
        {ingredients.map(ingredient => (
          <option key={ingredient.id} value={ingredient.id}>
            {ingredient.name}
          </option>
        ))}
      </select>
      <select
        value={days}
        onChange={event => onDaysChange(Number(event.target.value))}
        className="h-9 rounded-lg border border-stone-200 bg-white px-3 text-sm text-stone-700 outline-none focus:border-brand-600 focus:ring-2 focus:ring-brand-600/20"
      >
        <option value={30}>30 dias</option>
        <option value={90}>90 dias</option>
        <option value={180}>180 dias</option>
        <option value={365}>365 dias</option>
      </select>
    </div>
  )
}

function TimeSeriesChart({
  data,
  color,
  tooltipLabel,
}: {
  data: StockHistoryPoint[]
  color: string
  tooltipLabel: string
}) {
  if (!data.length) return <EmptyState />

  return (
    <div className="h-80">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 10, right: 24, bottom: 0, left: 0 }}>
          <CartesianGrid stroke="#E8E6E0" vertical={false} />
          <XAxis
            dataKey="date"
            tickFormatter={fmt.date}
            tick={{ fill: '#888780', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tickFormatter={fmt.compact}
            tick={{ fill: '#888780', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            formatter={value => [fmt.number(Number(value), 2), tooltipLabel]}
            labelFormatter={label => new Date(`${label}T00:00:00`).toLocaleDateString('pt-BR')}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={2.5}
            dot={false}
            activeDot={{ r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

function CategoryStockChart({ groups }: { groups: DashboardUnitCategoryGroup[] }) {
  const chartData = groups.flatMap(group =>
    group.items.map(item => ({
      ...item,
      label: `${item.name} · ${group.unit}`,
      unit: group.unit,
    })),
  )
  if (!chartData.length) return <EmptyState />

  return (
    <div className="h-80">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} layout="vertical" margin={{ top: 4, right: 20, bottom: 4, left: 16 }}>
          <CartesianGrid stroke="#E8E6E0" horizontal={false} />
          <XAxis
            type="number"
            tickFormatter={fmt.compact}
            tick={{ fill: '#888780', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="label"
            width={152}
            tickFormatter={value => shortLabel(String(value), 24)}
            tick={{ fill: '#5F5E5A', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            formatter={(value, _, payload) => [
              `${fmt.number(Number(value), 2)} ${payload.payload.unit}`,
              'Estoque',
            ]}
            labelFormatter={label => String(label)}
            cursor={{ fill: '#F5F4F1' }}
          />
          <Bar dataKey="value" name="Estoque" fill="#2D7A3A" radius={[0, 6, 6, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

function RankChart({
  data,
  color,
  valueLabel,
}: {
  data: Array<DashboardRankItem | DashboardCategoryItem>
  color: string
  valueLabel: string
}) {
  if (!data.length) return <EmptyState />

  return (
    <div className="h-72">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 20, bottom: 4, left: 12 }}>
          <CartesianGrid stroke="#E8E6E0" horizontal={false} />
          <XAxis
            type="number"
            tickFormatter={fmt.compact}
            tick={{ fill: '#888780', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="name"
            width={128}
            tickFormatter={value => shortLabel(String(value))}
            tick={{ fill: '#5F5E5A', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            formatter={value => [fmt.number(Number(value), 2), valueLabel]}
            labelFormatter={label => String(label)}
            cursor={{ fill: '#F5F4F1' }}
          />
          <Bar dataKey="value" name={valueLabel} fill={color} radius={[0, 6, 6, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

function ProductRankingList({ groups }: { groups: DashboardUnitRankGroup[] }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {groups.map(group => (
        <div key={group.unit} className="rounded-lg border border-stone-100 overflow-hidden">
          <div className="bg-stone-50 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-stone-500">
            {group.unit}
          </div>
          <ol className="divide-y divide-stone-100">
            {group.items.map((item, index) => (
              <li key={item.id} className="px-3 py-3 flex items-center gap-3">
                <span className="size-6 rounded-full bg-stone-100 text-stone-500 text-xs font-bold flex items-center justify-center flex-shrink-0">
                  {index + 1}
                </span>
                <span className="flex-1 min-w-0">
                  <span className="block font-medium text-stone-900 truncate">{item.name}</span>
                  <span className="block text-xs text-stone-400 truncate">{item.category}</span>
                </span>
                <span className="tabular-nums font-semibold text-stone-700">
                  {fmt.number(item.value, 2)}
                </span>
              </li>
            ))}
          </ol>
        </div>
      ))}
    </div>
  )
}

function severityClass(severity: DashboardAlert['severity']) {
  if (severity === 'Crítico') return 'bg-red-50 text-saltim-red border-red-100'
  if (severity === 'Atenção') return 'bg-orange-50 text-saltim-orange border-orange-100'
  return 'bg-blue-50 text-saltim-blue border-blue-100'
}

export function DashboardPage() {
  const [categoryId, setCategoryId] = useState('')
  const [ingredientId, setIngredientId] = useState('')
  const [days, setDays] = useState(90)

  const { data, isLoading, isError } = useDashboard()
  const filterArgs = {
    categoryId: categoryId || undefined,
    ingredientId: ingredientId || undefined,
    days,
  }
  const { data: stockHistory = [] } = useStockHistory(filterArgs)
  const { data: salesHistory = [] } = useSalesHistory(filterArgs)
  const { data: recipes = [] } = useRecipeRanking(filterArgs)

  const hour = new Date().getHours()
  const period = hour < 12 ? 'Bom dia' : hour < 18 ? 'Boa tarde' : 'Boa noite'
  const dateStr = new Date().toLocaleDateString('pt-BR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  })

  const ingredientOptions = useMemo(() => {
    const ingredients = data?.filters.ingredients ?? []
    if (!categoryId) return ingredients
    return ingredients.filter(item => item.category_id === categoryId)
  }, [categoryId, data?.filters.ingredients])

  const renderFilters = () =>
    data ? (
      <UnitFilters
        categoryId={categoryId}
        ingredientId={ingredientId}
        days={days}
        categories={data.filters.categories}
        ingredients={ingredientOptions}
        onCategoryChange={value => {
          setCategoryId(value)
          setIngredientId('')
        }}
        onIngredientChange={setIngredientId}
        onDaysChange={setDays}
      />
    ) : null

  if (isError) {
    return (
      <div className="flex flex-col h-screen bg-surface overflow-auto">
        <div className="bg-white border-b border-stone-200 px-8 py-5 flex-shrink-0">
          <h1 className="text-xl font-semibold text-stone-900">Dashboard</h1>
          <p className="text-sm text-stone-400 mt-0.5">Falha ao carregar dados</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-screen bg-surface overflow-auto">
      <div className="bg-white border-b border-stone-200 px-8 py-5 flex-shrink-0">
        <h1 className="text-xl font-semibold text-stone-900">{period}, Fernanda</h1>
        <p className="text-sm text-stone-400 mt-0.5 capitalize">{dateStr} · Saltim Café</p>
      </div>

      <div className="flex-1 p-6 lg:p-8 flex flex-col gap-6">
        {isLoading || !data ? (
          <div className="bg-white rounded-xl border border-stone-200 p-8 text-sm text-stone-400">
            Carregando dashboard...
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-4">
              <StatCard
                label="Ingredientes cadastrados"
                value={fmt.number(data.cards.total_items, 0)}
                detail={`${fmt.number(data.cards.total_stock_qty, 2)} em estoque atual, sem Produção`}
                tone="ink"
              />
              <StatCard
                label="Categorias com mais itens"
                value={data.cards.top_categories_by_unit.map(itemWithUnit).join(' · ')}
                detail={unitDetail(data.cards.top_categories_by_unit)}
                tone="green"
              />
              <StatCard
                label="Categorias com menos itens"
                value={data.cards.bottom_categories_by_unit.map(itemWithUnit).join(' · ')}
                detail={unitDetail(data.cards.bottom_categories_by_unit)}
                tone="orange"
              />
              <StatCard
                label="Ingredientes com mais itens"
                value={data.cards.top_products_by_unit.map(itemWithUnit).join(' · ')}
                detail={unitDetail(data.cards.top_products_by_unit)}
                tone="blue"
              />
              <StatCard
                label="Ingredientes com menos itens"
                value={data.cards.bottom_products_by_unit.map(itemWithUnit).join(' · ')}
                detail={unitDetail(data.cards.bottom_products_by_unit)}
                tone="red"
              />
            </div>

            <Panel title="Estoque ao longo do tempo" action={renderFilters()}>
              <TimeSeriesChart data={stockHistory} color="#52B9EB" tooltipLabel="Estoque" />
            </Panel>

            <Panel title="Alertas operacionais de compra">
              <div className="overflow-x-auto">
                <table className="w-full min-w-[760px] text-sm">
                  <thead>
                    <tr className="text-left text-xs font-semibold uppercase tracking-wide text-stone-400 border-b border-stone-100">
                      <th className="py-3 pr-4">Ingrediente</th>
                      <th className="py-3 pr-4">Categoria</th>
                      <th className="py-3 pr-4 text-right">Estoque</th>
                      <th className="py-3 pr-4 text-right">Uso/dia</th>
                      <th className="py-3 pr-4 text-right">Cobertura</th>
                      <th className="py-3 pr-4 text-right">Sugestão</th>
                      <th className="py-3">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.alerts.map(alert => (
                      <tr key={alert.ingredient_id} className="border-b border-stone-100 last:border-0">
                        <td className="py-3 pr-4 font-medium text-stone-900">{alert.name}</td>
                        <td className="py-3 pr-4 text-stone-500">{alert.category}</td>
                        <td className="py-3 pr-4 text-right tabular-nums text-stone-700">
                          {fmt.number(alert.current_qty, 2)} {alert.unit}
                        </td>
                        <td className="py-3 pr-4 text-right tabular-nums text-stone-700">
                          {fmt.number(alert.avg_daily_output, 2)} {alert.unit}
                        </td>
                        <td className="py-3 pr-4 text-right tabular-nums text-stone-700">
                          {fmt.number(alert.coverage_days, 1)} dias
                        </td>
                        <td className="py-3 pr-4 text-right tabular-nums text-stone-700">
                          {fmt.number(alert.suggested_qty, 2)} {alert.unit}
                        </td>
                        <td className="py-3">
                          <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${severityClass(alert.severity)}`}>
                            {alert.severity}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {!data.alerts.length && <EmptyState />}
              </div>
            </Panel>

            <Panel title="Vendas ao longo do tempo" action={renderFilters()}>
              <TimeSeriesChart data={salesHistory} color="#F07820" tooltipLabel="Vendas" />
            </Panel>

            <Panel title="Receitas que mais saem" action={renderFilters()}>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[620px] text-sm">
                  <thead>
                    <tr className="text-left text-xs font-semibold uppercase tracking-wide text-stone-400 border-b border-stone-100">
                      <th className="py-3 pr-4">Receita</th>
                      <th className="py-3 pr-4 text-right">Unidades vendidas</th>
                      <th className="py-3 text-right">Faturamento</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recipes.map(recipe => (
                      <tr key={recipe.id} className="border-b border-stone-100 last:border-0">
                        <td className="py-3 pr-4 font-medium text-stone-900">{recipe.name}</td>
                        <td className="py-3 pr-4 text-right tabular-nums text-stone-700">
                          {fmt.number(recipe.quantity, 0)}
                        </td>
                        <td className="py-3 text-right tabular-nums text-stone-700">
                          {fmt.currency(recipe.revenue)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {!recipes.length && <EmptyState />}
              </div>
            </Panel>

            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
              <Panel title="Ingredientes com mais itens">
                <ProductRankingList groups={data.top_stock_products_by_unit} />
              </Panel>
              <Panel title="Ingredientes com menos itens">
                <ProductRankingList groups={data.bottom_stock_products_by_unit} />
              </Panel>
              <Panel title="Categorias com mais itens">
                <CategoryStockChart groups={data.top_stock_categories_by_unit} />
              </Panel>
              <Panel title="Ingredientes mais utilizados">
                <RankChart data={data.top_output_products} color="#1A1918" valueLabel="Uso" />
              </Panel>
              <Panel title="Ingredientes menos utilizados">
                <RankChart data={data.bottom_output_products} color="#888780" valueLabel="Uso" />
              </Panel>
              <Panel title="Categoria mais utilizada">
                <RankChart data={data.top_output_categories} color="#2D7A3A" valueLabel="Uso" />
              </Panel>
              <Panel title="Categoria menos utilizada">
                <RankChart data={data.bottom_output_categories} color="#EDE0B4" valueLabel="Uso" />
              </Panel>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
