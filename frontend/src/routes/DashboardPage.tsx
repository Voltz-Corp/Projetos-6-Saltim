import { useEffect, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { createRoute } from '@tanstack/react-router';
import { AnimatePresence, motion } from 'motion/react';
import {
  Download,
  Filter,
  Flag,
  Gauge,
  Package,
  TriangleAlert,
  X,
} from 'lucide-react';
import {
  Bar,
  BarChart,
  Cell,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { rootRoute } from './Root';
import {
  AppCheckboxMultiSelect,
  AppSelect,
  type SelectOption,
} from '../components/AppSelect';
import { CoffeeLoading } from '../components/CoffeeLoading';
import {
  DateFilterControl,
  type DateFilterMode,
} from '../components/DateFilterControl';
import { FilterField } from '../components/FilterPanel';
import { KpiCard, type KpiTone } from '../components/KpiCard';
import {
  downloadDashboardExport,
  type DashboardExportFormat,
} from '../lib/exportData';
import { useAppearance } from '../theme/appearance';
import {
  useDashboard,
  useRecipeRanking,
  useRevenueSummary,
  useSalesHistory,
  useStockHistory,
  useWeekdayOrders,
  type DashboardAlert,
  type DashboardCategoryItem,
  type DashboardKpi,
  type DashboardNamedMetric,
  type DashboardRankItem,
  type DashboardUnitCategoryGroup,
  type DashboardUnitRankGroup,
  type StockHistoryPoint,
} from '../hooks/useDashboard';

export const dashboardRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  component: DashboardPage,
});

type RankMode = 'top' | 'bottom';
type DashboardUnit = 'KG' | 'UND' | 'L';
type SeriesMetric = 'stock' | 'sales';
type RevenuePeriod = 'monthly' | 'quarterly';
type RankingKind =
  | 'stock_ingredient'
  | 'stock_category'
  | 'usage_ingredient'
  | 'recipes';

const UNIT_OPTIONS: DashboardUnit[] = ['KG', 'UND', 'L'];
const DONUT_COLORS = [
  'var(--theme-chart-1)',
  'var(--theme-chart-2)',
  'var(--theme-chart-3)',
  'var(--theme-chart-4)',
  'var(--theme-chart-5)',
  'var(--theme-chart-6)',
  'var(--theme-chart-7)',
  'var(--theme-chart-8)',
];
const chartAxisTick = { fill: 'var(--theme-chart-axis)', fontSize: 11 };
const chartTooltipStyle = {
  backgroundColor: 'var(--theme-card)',
  borderColor: 'var(--theme-stone-200)',
  color: 'var(--theme-stone-900)',
};
const chartTooltipLabelStyle = { color: 'var(--theme-stone-900)' };
const DASHBOARD_EXPORT_OPTIONS: Array<{
  value: DashboardExportFormat;
  label: string;
}> = [
  { value: 'pdf', label: 'PDF' },
  { value: 'excel', label: 'Excel' },
];

interface DashboardGlobalFilterState {
  days: number;
  allPeriod: boolean;
  categoryIds: string[];
  eventTypes: string[];
  selectedYears: string[];
  selectedMonths: string[];
  dateMode: DateFilterMode;
  rangeStart: string;
  rangeEnd: string;
}

const DEFAULT_GLOBAL_FILTERS: DashboardGlobalFilterState = {
  days: 90,
  allPeriod: false,
  categoryIds: [],
  eventTypes: [],
  selectedYears: [],
  selectedMonths: [],
  dateMode: 'all',
  rangeStart: '',
  rangeEnd: '',
};

const fmt = {
  number: (value: number, maximumFractionDigits = 2) =>
    value.toLocaleString('pt-BR', {
      minimumFractionDigits: maximumFractionDigits,
      maximumFractionDigits,
    }),
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
};

function displayName(value: string) {
  return value
    .toLocaleLowerCase('pt-BR')
    .replace(/(^|[\s/.-])(\S)/g, (match) => match.toLocaleUpperCase('pt-BR'));
}

function groupItems<T extends { unit: string; items: unknown[] }>(
  groups: T[],
  unit: DashboardUnit,
): T['items'] {
  return (groups.find((group) => group.unit === unit)?.items ??
    []) as T['items'];
}

function StatCard({ item }: { item: DashboardKpi }) {
  const value =
    item.id === 'top_recipe' || item.id === 'critical_ingredient'
      ? displayName(item.value)
      : item.value;
  const isTopRecipe = item.id === 'top_recipe';
  const shouldShowDetail = item.id !== 'coverage' && Boolean(item.detail);
  const tone: KpiTone =
    item.id === 'critical_ingredient'
      ? 'red'
      : item.id === 'top_recipe'
        ? 'orange'
        : item.id === 'coverage'
          ? 'blue'
          : 'green';

  return (
    <KpiCard
      icon={kpiIconById[item.id]}
      label={item.label}
      value={value}
      detail={shouldShowDetail ? item.detail : undefined}
      tone={tone}
      truncateValue={isTopRecipe}
      showComparisonBadge={false}
      comparisonLabel={item.trend_label}
      comparisonDirection={item.trend_direction}
    />
  );
}

const kpiIconById = {
  ingredients: Package,
  coverage: Gauge,
  top_recipe: Flag,
  critical_ingredient: TriangleAlert,
} satisfies Record<DashboardKpi['id'], typeof Package>;

function Panel({
  title,
  subtitle,
  children,
  action,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <section className="bg-white rounded-xl border border-stone-200 min-w-0 overflow-visible">
      <div className="px-5 py-4 border-b border-stone-100 flex flex-col gap-3 lg:flex-row lg:items-center">
        <div className="flex flex-wrap items-baseline gap-2 flex-1 min-w-0">
          <h2 className="text-sm font-semibold text-stone-900">{title}</h2>
          {subtitle && (
            <span className="text-xs font-medium text-stone-400">
              {subtitle}
            </span>
          )}
        </div>
        {action}
      </div>
      <div className="p-4">{children}</div>
    </section>
  );
}

function EmptyState() {
  return (
    <div className="h-56 flex items-center justify-center text-sm text-stone-400">
      Sem dados para exibir
    </div>
  );
}

function optionsFrom<T extends { id: string; name: string }>(
  items: T[],
  allLabel: string,
): SelectOption[] {
  return [
    { value: '', label: allLabel },
    ...items.map((item) => ({ value: item.id, label: displayName(item.name) })),
  ];
}

function unitOptions(): SelectOption[] {
  return UNIT_OPTIONS.map((unit) => ({ value: unit, label: unit }));
}

function FilterButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex items-center gap-2 rounded-lg border border-stone-200 bg-white px-3 py-2 text-xs font-bold text-stone-700 shadow-sm transition hover:border-brand-200 hover:bg-brand-50 hover:text-brand-700"
    >
      <Filter className="size-4" strokeWidth={1.9} />
      Filtros
    </button>
  );
}

function FilterMenu({
  open,
  onToggle,
  onClose,
  children,
}: {
  open: boolean;
  onToggle: () => void;
  onClose: () => void;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;

    function handlePointerDown(event: MouseEvent) {
      if (!ref.current?.contains(event.target as Node)) {
        onClose();
      }
    }

    document.addEventListener('mousedown', handlePointerDown);
    return () => document.removeEventListener('mousedown', handlePointerDown);
  }, [onClose, open]);

  return (
    <div ref={ref} className="relative">
      <FilterButton onClick={onToggle} />
      {open && <FilterPopover>{children}</FilterPopover>}
    </div>
  );
}

function FilterPopover({ children }: { children: ReactNode }) {
  return (
    <div className="absolute right-0 top-[calc(100%+8px)] z-30 w-[min(82vw,360px)] rounded-xl border border-stone-200 bg-white p-3 shadow-[0_18px_40px_rgba(26,25,24,0.14)]">
      <div className="grid gap-2">{children}</div>
    </div>
  );
}

function ToggleSwitch({
  checked,
  label,
  onChange,
}: {
  checked: boolean;
  label: string;
  onChange: (checked: boolean) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className="flex items-center justify-between rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm font-semibold text-stone-700 transition hover:bg-stone-50"
    >
      <span>{label}</span>
      <span
        className={[
          'flex h-5 w-9 items-center rounded-full p-0.5 transition-colors',
          checked ? 'bg-brand-600' : 'bg-stone-200',
        ].join(' ')}
      >
        <span
          className={[
            'size-4 rounded-full bg-white shadow transition-transform',
            checked ? 'translate-x-4' : 'translate-x-0',
          ].join(' ')}
        />
      </span>
    </button>
  );
}

function CollapsibleSection({
  title,
  defaultOpen = true,
  children,
}: {
  title: string;
  defaultOpen?: boolean;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <section className="border-b border-stone-100 py-5 first:pt-0">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-center justify-between text-left"
      >
        <span className="text-xs font-black uppercase tracking-wide text-stone-500">
          {title}
        </span>
        <span className="text-lg font-bold text-brand-600">{open ? '-' : '+'}</span>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            className="overflow-hidden"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
          >
            <div className="mt-3 grid gap-3">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
}

function activeFilterCount(filters: DashboardGlobalFilterState) {
  let count = 0;
  if (filters.allPeriod) count += 1;
  else if (filters.days !== DEFAULT_GLOBAL_FILTERS.days) count += 1;
  if (filters.categoryIds.length) count += 1;
  if (filters.eventTypes.length) count += 1;
  if (filters.selectedYears.length) count += 1;
  if (filters.selectedMonths.length) count += 1;
  if (filters.dateMode !== 'all' && (filters.rangeStart || filters.rangeEnd)) count += 1;
  return count;
}

function DashboardFilterDrawer({
  open,
  filters,
  categories,
  months,
  onChange,
  onOpen,
  onClose,
  onApply,
  onClear,
  appliedCount,
}: {
  open: boolean;
  filters: DashboardGlobalFilterState;
  categories: DashboardCategoryItem[];
  months: Array<{ key: string; label: string }>;
  onChange: (filters: DashboardGlobalFilterState) => void;
  onOpen: () => void;
  onClose: () => void;
  onApply: () => void;
  onClear: () => void;
  appliedCount: number;
}) {
  const categoryOptions = optionsFrom(categories, '').filter(
    (option) => option.value,
  );
  const yearOptions = Array.from(
    new Set(months.map((month) => month.key.slice(0, 4))),
  ).map((year) => ({ value: year, label: year }));
  const monthOptions = [
    'Janeiro',
    'Fevereiro',
    'Março',
    'Abril',
    'Maio',
    'Junho',
    'Julho',
    'Agosto',
    'Setembro',
    'Outubro',
    'Novembro',
    'Dezembro',
  ].map((label, index) => ({ value: String(index + 1), label }));

  function update(patch: Partial<DashboardGlobalFilterState>) {
    onChange({ ...filters, ...patch });
  }

  function toggleEvent(value: string, checked: boolean) {
    update({
      eventTypes: checked
        ? Array.from(new Set([...filters.eventTypes, value]))
        : filters.eventTypes.filter((item) => item !== value),
    });
  }

  return (
    <>
      <button
        type="button"
        onClick={open ? onClose : onOpen}
        className="fixed right-0 top-1/2 z-40 flex -translate-y-1/2 items-center gap-2 rounded-l-xl bg-brand-600 px-2 py-4 text-xs font-black uppercase tracking-wide text-white shadow-[0_14px_34px_rgba(26,25,24,0.18)] transition hover:bg-brand-700"
        aria-label="Abrir filtros globais"
      >
        <Filter className="size-4" strokeWidth={2} />
        {appliedCount > 0 && (
          <span className="absolute -left-2 -top-2 flex size-5 items-center justify-center rounded-full bg-saltim-red text-[10px] font-black text-white">
            {appliedCount}
          </span>
        )}
      </button>

      {open && (
        <button
          type="button"
          className="fixed inset-0 z-40 bg-saltim-dark/20"
          onClick={onClose}
          aria-label="Fechar filtros"
        />
      )}

      <aside
        className={[
          'fixed right-0 top-0 z-50 h-screen w-[min(92vw,390px)] transform bg-white shadow-[0_20px_60px_rgba(26,25,24,0.22)] transition-transform duration-200',
          open ? 'translate-x-0' : 'translate-x-full',
        ].join(' ')}
      >
        <div className="flex h-[73px] items-center justify-between border-b border-stone-200 px-5">
          <div>
            <h2 className="text-sm font-black text-stone-900">
              Filtros globais
            </h2>
            <p className="text-xs text-stone-400">
              Aplicados ao dashboard inteiro
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex size-9 items-center justify-center rounded-lg text-stone-500 transition hover:bg-stone-100 hover:text-stone-900"
            aria-label="Fechar"
          >
            <X className="size-5" strokeWidth={1.9} />
          </button>
        </div>

        <div className="flex h-[calc(100vh-73px)] flex-col overflow-y-auto p-5">
            <CollapsibleSection title="Tempo">
              <FilterField label="Período">
                <DaysSelect
                  value={filters.days}
                  allPeriod={filters.allPeriod}
                  onChange={(days) => update({ days })}
                  onAllPeriodChange={(allPeriod) => update({ allPeriod })}
                />
              </FilterField>
              <FilterField label="Anos">
                <AppCheckboxMultiSelect
                  value={filters.selectedYears}
                  options={yearOptions}
                  onChange={(selectedYears) => update({ selectedYears })}
                  placeholder="Selecionar anos"
                />
              </FilterField>
              <FilterField label="Meses">
                <AppCheckboxMultiSelect
                  value={filters.selectedMonths}
                  options={monthOptions}
                  onChange={(selectedMonths) => update({ selectedMonths })}
                  placeholder="Selecionar meses"
                />
              </FilterField>
              <FilterField label="Data">
                <DateFilterControl
                  mode={filters.dateMode}
                  dateFrom={filters.rangeStart}
                  dateTo={filters.rangeEnd}
                  onChange={(value) =>
                    update({
                      dateMode: value.mode,
                      rangeStart: value.dateFrom,
                      rangeEnd: value.dateTo,
                    })
                  }
                />
              </FilterField>
            </CollapsibleSection>

            <CollapsibleSection title="Categorias" defaultOpen={false}>
              <FilterField label="Categorias">
                <AppCheckboxMultiSelect
                  value={filters.categoryIds}
                  options={categoryOptions}
                  onChange={(categoryIds) => update({ categoryIds })}
                  placeholder="Todas as categorias"
                />
              </FilterField>
            </CollapsibleSection>

            <CollapsibleSection title="Eventos" defaultOpen={false}>
              <ToggleSwitch
                checked={filters.eventTypes.includes('holiday')}
                label="Feriados"
                onChange={(checked) => toggleEvent('holiday', checked)}
              />
              <ToggleSwitch
                checked={filters.eventTypes.includes('rain')}
                label="Dia de chuva"
                onChange={(checked) => toggleEvent('rain', checked)}
              />
              <ToggleSwitch
                checked={filters.eventTypes.includes('promo')}
                label="Dia promocional"
                onChange={(checked) => toggleEvent('promo', checked)}
              />
            </CollapsibleSection>

            <div className="mt-auto flex gap-2 border-t border-stone-100 pt-4">
              <button
                type="button"
                onClick={onClear}
                className="flex-1 rounded-lg border border-stone-200 px-3 py-2 text-sm font-bold text-stone-600 transition hover:bg-stone-50"
              >
                Limpar
              </button>
              <button
                type="button"
                onClick={onApply}
                className="flex-1 rounded-lg bg-brand-600 px-3 py-2 text-sm font-bold text-white transition hover:bg-brand-700"
              >
                Aplicar
              </button>
            </div>
        </div>
      </aside>
    </>
  );
}

function TrendFilters({
  seriesMetrics,
  onSeriesMetricsChange,
}: {
  seriesMetrics: SeriesMetric[];
  onSeriesMetricsChange: (value: SeriesMetric[]) => void;
}) {
  return (
    <div className="grid gap-2">
      <FilterField label="Visualização">
        <AppCheckboxMultiSelect
          value={seriesMetrics}
          options={[
            { value: 'sales', label: 'Vendas' },
            { value: 'stock', label: 'Estoque' },
          ]}
          onChange={(value) => onSeriesMetricsChange(value as SeriesMetric[])}
          className="w-full"
        />
      </FilterField>
    </div>
  );
}

function DaysSelect({
  value,
  allPeriod = false,
  onChange,
  onAllPeriodChange,
}: {
  value: number;
  allPeriod?: boolean;
  onChange: (value: number) => void;
  onAllPeriodChange?: (value: boolean) => void;
}) {
  return (
    <AppSelect
      value={allPeriod ? 'all' : String(value)}
      options={[
        { value: 'all', label: 'Todo o período' },
        { value: '30', label: '30 dias' },
        { value: '90', label: '90 dias' },
        { value: '180', label: '180 dias' },
        { value: '365', label: '365 dias' },
      ]}
      onChange={(selected) => {
        if (selected === 'all') {
          onAllPeriodChange?.(true);
          return;
        }
        onAllPeriodChange?.(false);
        onChange(Number(selected || value));
      }}
      className="w-full"
    />
  );
}

function RankingFilters({
  kind,
  mode,
  unit,
  recipeIngredientId,
  ingredients,
  onKindChange,
  onModeChange,
  onUnitChange,
  onRecipeIngredientChange,
}: {
  kind: RankingKind;
  mode: RankMode;
  unit: DashboardUnit;
  recipeIngredientId: string;
  ingredients: Array<{ id: string; name: string }>;
  onKindChange: (value: RankingKind) => void;
  onModeChange: (value: RankMode) => void;
  onUnitChange: (value: DashboardUnit) => void;
  onRecipeIngredientChange: (value: string) => void;
}) {
  const isRecipe = kind === 'recipes';
  const modeOptions =
    kind === 'stock_ingredient' || kind === 'stock_category'
      ? [
          { value: 'top', label: 'Mais itens' },
          { value: 'bottom', label: 'Menos itens' },
        ]
      : [
          { value: 'top', label: 'Mais utilizados' },
          { value: 'bottom', label: 'Menos utilizados' },
        ];

  return (
    <div className="grid gap-2">
      <FilterField label="Ranking">
        <AppSelect
          value={kind}
          options={[
            { value: 'stock_ingredient', label: 'Estoque por ingrediente' },
            { value: 'stock_category', label: 'Estoque por categoria' },
            { value: 'usage_ingredient', label: 'Uso por ingrediente' },
            { value: 'recipes', label: 'Receitas que mais saem' },
          ]}
          onChange={(value) =>
            onKindChange((value || 'stock_ingredient') as RankingKind)
          }
          className="w-full"
        />
      </FilterField>
      {!isRecipe && (
        <>
          <FilterField label="Ordenação">
            <AppSelect
              value={mode}
              options={modeOptions}
              onChange={(value) => onModeChange((value || 'top') as RankMode)}
              className="w-full"
            />
          </FilterField>
          <FilterField label="Unidade">
            <AppSelect
              value={unit}
              options={unitOptions()}
              onChange={(value) =>
                onUnitChange((value || 'KG') as DashboardUnit)
              }
              className="w-full"
            />
          </FilterField>
        </>
      )}
      {isRecipe && (
        <>
          <FilterField label="Ingrediente da receita">
            <AppSelect
              value={recipeIngredientId}
              options={optionsFrom(ingredients, 'Todos os ingredientes')}
              onChange={onRecipeIngredientChange}
              className="w-full"
            />
          </FilterField>
        </>
      )}
    </div>
  );
}

function RankingTable({
  rows,
  unit,
  label,
  valueTooltip,
  entityLabel,
}: {
  rows: Array<DashboardRankItem | DashboardCategoryItem>;
  unit: DashboardUnit;
  label: string;
  valueTooltip: string;
  entityLabel: string;
}) {
  if (!rows.length) return <EmptyState />;

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[620px] text-sm">
        <thead>
          <tr className="text-left text-xs font-semibold uppercase tracking-wide text-stone-400 border-b border-stone-100">
            <th className="py-3 pr-4 w-14">#</th>
            <th className="py-3 pr-4">{entityLabel}</th>
            <th className="py-3 pr-4">Unidade</th>
            <th className="py-3 text-right">{label}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((item, index) => (
            <tr
              key={item.id}
              className="border-b border-stone-100 last:border-0"
            >
              <td className="py-3 pr-4 text-xs font-bold text-stone-400">
                {index + 1}
              </td>
              <td
                className="py-3 pr-4 font-medium text-stone-900"
                title={
                  'category' in item && item.category
                    ? displayName(item.category)
                    : undefined
                }
              >
                <span className="block max-w-[360px] truncate">
                  {displayName(item.name)}
                </span>
              </td>
              <td className="py-3 pr-4 text-stone-500">{item.unit ?? unit}</td>
              <td
                className="py-3 text-right tabular-nums font-semibold text-stone-700"
                title={`${valueTooltip}: ${fmt.number(item.value, 2)} ${item.unit ?? unit}`}
              >
                {fmt.number(item.value, 2)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RecipeRankingTable({
  recipes,
}: {
  recipes: Array<{
    id: string;
    name: string;
    quantity: number;
    revenue: number;
  }>;
}) {
  if (!recipes.length) return <EmptyState />;

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[620px] text-sm">
        <thead>
          <tr className="text-left text-xs font-semibold uppercase tracking-wide text-stone-400 border-b border-stone-100">
            <th className="py-3 pr-4 w-14">#</th>
            <th className="py-3 pr-4">Receita</th>
            <th className="py-3 pr-4 text-right">Unidades vendidas</th>
            <th className="py-3 text-right">Faturamento</th>
          </tr>
        </thead>
        <tbody>
          {recipes.map((recipe, index) => (
            <tr
              key={recipe.id}
              className="border-b border-stone-100 last:border-0"
            >
              <td className="py-3 pr-4 text-xs font-bold text-stone-400">
                {index + 1}
              </td>
              <td className="py-3 pr-4 font-medium text-stone-900">
                {displayName(recipe.name)}
              </td>
              <td
                className="py-3 pr-4 text-right tabular-nums text-stone-700"
                title="Quantidade vendida no período filtrado"
              >
                {fmt.number(recipe.quantity, 2)} UND
              </td>
              <td
                className="py-3 text-right tabular-nums text-stone-700"
                title="Faturamento bruto estimado no período filtrado"
              >
                {fmt.currency(recipe.revenue)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RevenueFilters({
  period,
  onPeriodChange,
}: {
  period: RevenuePeriod;
  onPeriodChange: (value: RevenuePeriod) => void;
}) {
  return (
    <FilterField label="Agrupamento">
      <AppSelect
        value={period}
        options={[
          { value: 'monthly', label: 'Por mês' },
          { value: 'quarterly', label: 'Por quarter' },
        ]}
        onChange={(value) =>
          onPeriodChange((value || 'monthly') as RevenuePeriod)
        }
        className="w-full"
      />
    </FilterField>
  );
}

function CategoryUsageFilters({
  mode,
  unit,
  onModeChange,
  onUnitChange,
}: {
  mode: RankMode;
  unit: DashboardUnit;
  onModeChange: (value: RankMode) => void;
  onUnitChange: (value: DashboardUnit) => void;
}) {
  return (
    <div className="grid gap-2">
      <FilterField label="Ordenação">
        <AppSelect
          value={mode}
          options={[
            { value: 'top', label: 'Mais utilizadas' },
            { value: 'bottom', label: 'Menos utilizadas' },
          ]}
          onChange={(value) => onModeChange((value || 'top') as RankMode)}
          className="w-full"
        />
      </FilterField>
      <FilterField label="Unidade">
        <AppSelect
          value={unit}
          options={unitOptions()}
          onChange={(value) => onUnitChange((value || 'KG') as DashboardUnit)}
          className="w-full"
        />
      </FilterField>
    </div>
  );
}

function RevenueBarChart({ data }: { data: DashboardNamedMetric[] }) {
  if (!data.length) return <EmptyState />;

  return (
    <div className="h-72">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          margin={{ top: 8, right: 12, bottom: 0, left: 0 }}
        >
          <CartesianGrid stroke="var(--theme-chart-grid)" vertical={false} />
          <XAxis
            dataKey="label"
            tick={chartAxisTick}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tickFormatter={fmt.compact}
            tick={chartAxisTick}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            formatter={(value) => [fmt.currency(Number(value)), 'Faturamento']}
            cursor={{ fill: 'var(--theme-chart-cursor)' }}
            contentStyle={chartTooltipStyle}
            labelStyle={chartTooltipLabelStyle}
          />
          <Bar dataKey="value" fill="var(--theme-chart-1)" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function WeekdayOrdersBarChart({ data }: { data: DashboardNamedMetric[] }) {
  if (!data.length) return <EmptyState />;

  return (
    <div className="h-72">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          margin={{ top: 8, right: 12, bottom: 0, left: 0 }}
        >
          <CartesianGrid stroke="var(--theme-chart-grid)" vertical={false} />
          <XAxis
            dataKey="label"
            tick={chartAxisTick}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tickFormatter={fmt.compact}
            tick={chartAxisTick}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            formatter={(value) => [fmt.number(Number(value), 2), 'Pedidos']}
            cursor={{ fill: 'var(--theme-chart-cursor)' }}
            contentStyle={chartTooltipStyle}
            labelStyle={chartTooltipLabelStyle}
          />
          <Bar dataKey="value" fill="var(--theme-chart-2)" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function CategoryUsageDonutChart({
  data,
  unit,
}: {
  data: DashboardCategoryItem[];
  unit: DashboardUnit;
}) {
  const chartData = data.filter((item) => item.value > 0);
  const total = chartData.reduce((sum, item) => sum + item.value, 0);
  if (!chartData.length || total <= 0) return <EmptyState />;

  return (
    <div className="h-72">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Tooltip
            contentStyle={chartTooltipStyle}
            labelStyle={chartTooltipLabelStyle}
            formatter={(value, _name, props) => {
              const percent = (Number(value) / total) * 100;
              return [
                `${fmt.number(percent, 1)}% · ${fmt.number(Number(value), 2)} ${unit}`,
                displayName(String(props.payload.name)),
              ];
            }}
          />
          <Pie
            data={chartData}
            dataKey="value"
            nameKey="name"
            innerRadius="58%"
            outerRadius="82%"
            paddingAngle={2}
          >
            {chartData.map((item, index) => (
              <Cell
                key={item.id}
                fill={DONUT_COLORS[index % DONUT_COLORS.length]}
              />
            ))}
          </Pie>
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

function CombinedHistoryChart({
  stock,
  sales,
  metrics,
}: {
  stock: StockHistoryPoint[];
  sales: StockHistoryPoint[];
  metrics: SeriesMetric[];
}) {
  const showStock = metrics.includes('stock');
  const showSales = metrics.includes('sales');
  const data = useMemo(() => {
    const byDate = new Map<
      string,
      { date: string; stock?: number; sales?: number }
    >();
    if (showStock) {
      stock.forEach((point) =>
        byDate.set(point.date, {
          ...(byDate.get(point.date) ?? { date: point.date }),
          stock: point.value,
        }),
      );
    }
    if (showSales) {
      sales.forEach((point) =>
        byDate.set(point.date, {
          ...(byDate.get(point.date) ?? { date: point.date }),
          sales: point.value,
        }),
      );
    }
    return Array.from(byDate.values()).sort((a, b) =>
      a.date.localeCompare(b.date),
    );
  }, [sales, showSales, showStock, stock]);

  if (!data.length) return <EmptyState />;

  return (
    <div className="h-80">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={data}
          margin={{ top: 10, right: 24, bottom: 0, left: 0 }}
        >
          <CartesianGrid stroke="var(--theme-chart-grid)" vertical={false} />
          <XAxis
            dataKey="date"
            tickFormatter={fmt.date}
            tick={chartAxisTick}
            axisLine={false}
            tickLine={false}
            interval="preserveStartEnd"
            minTickGap={24}
          />
          {showStock && (
            <YAxis
              yAxisId="stock"
              tickFormatter={fmt.compact}
              tick={{ fill: 'var(--theme-chart-2)', fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
          )}
          {showSales && (
            <YAxis
              yAxisId="sales"
              orientation={showStock ? 'right' : 'left'}
              tickFormatter={fmt.compact}
              tick={{ fill: 'var(--theme-chart-1)', fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
          )}
          <Tooltip
            contentStyle={chartTooltipStyle}
            labelStyle={chartTooltipLabelStyle}
            formatter={(value, name) => [
              fmt.number(Number(value), 2),
              name === 'stock' || name === 'Estoque' ? 'Estoque' : 'Vendas',
            ]}
            labelFormatter={(label) =>
              new Date(`${label}T00:00:00`).toLocaleDateString('pt-BR')
            }
          />
          <Legend
            verticalAlign="top"
            align="right"
            iconType="line"
            wrapperStyle={{ fontSize: 12, paddingBottom: 8 }}
          />
          {showStock && (
            <Line
              name="Estoque"
              yAxisId="stock"
              type="monotone"
              dataKey="stock"
              stroke="var(--theme-chart-2)"
              strokeWidth={2.5}
              dot={false}
              activeDot={{ r: 4 }}
              connectNulls
            />
          )}
          {showSales && (
            <Line
              name="Vendas"
              yAxisId="sales"
              type="monotone"
              dataKey="sales"
              stroke="var(--theme-chart-1)"
              strokeWidth={2.5}
              dot={false}
              activeDot={{ r: 4 }}
              connectNulls
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function severityClass(severity: DashboardAlert['severity']) {
  if (severity === 'Crítico') return 'saltim-danger-soft';
  if (severity === 'Atenção')
    return 'saltim-alert-soft';
  return 'saltim-info-soft';
}

export function DashboardPage() {
  const { themeId } = useAppearance();
  const [globalFiltersOpen, setGlobalFiltersOpen] = useState(false);
  const [draftFilters, setDraftFilters] =
    useState<DashboardGlobalFilterState>(DEFAULT_GLOBAL_FILTERS);
  const [globalFilters, setGlobalFilters] =
    useState<DashboardGlobalFilterState>(DEFAULT_GLOBAL_FILTERS);
  const [seriesMetrics, setSeriesMetrics] = useState<SeriesMetric[]>([
    'sales',
    'stock',
  ]);
  const [trendFiltersOpen, setTrendFiltersOpen] = useState(false);
  const [recipeIngredientId, setRecipeIngredientId] = useState('');
  const [rankingKind, setRankingKind] =
    useState<RankingKind>('stock_ingredient');
  const [rankingMode, setRankingMode] = useState<RankMode>('top');
  const [rankingUnit, setRankingUnit] = useState<DashboardUnit>('KG');
  const [rankingFiltersOpen, setRankingFiltersOpen] = useState(false);
  const [revenuePeriod, setRevenuePeriod] = useState<RevenuePeriod>('monthly');
  const [revenueFiltersOpen, setRevenueFiltersOpen] = useState(false);
  const [categoryUsageMode, setCategoryUsageMode] = useState<RankMode>('top');
  const [categoryUsageUnit, setCategoryUsageUnit] =
    useState<DashboardUnit>('KG');
  const [categoryUsageFiltersOpen, setCategoryUsageFiltersOpen] =
    useState(false);
  const [dashboardExportFormat, setDashboardExportFormat] =
    useState<DashboardExportFormat>('pdf');
  const [exportingFormat, setExportingFormat] =
    useState<DashboardExportFormat | null>(null);
  const [exportError, setExportError] = useState('');

  const activeCount = activeFilterCount(globalFilters);

  const apiFilters = useMemo(
    () => ({
      days: globalFilters.days,
      allPeriod: globalFilters.allPeriod,
      categoryIds: globalFilters.categoryIds,
      eventTypes: globalFilters.eventTypes,
      years: globalFilters.selectedYears,
      months: globalFilters.selectedMonths,
      dateFrom:
        globalFilters.dateMode === 'all' ? undefined : globalFilters.rangeStart || undefined,
      dateTo:
        globalFilters.dateMode === 'all' ? undefined : globalFilters.rangeEnd || undefined,
    }),
    [globalFilters],
  );

  const { data, isLoading, isError } = useDashboard(apiFilters);
  const filterArgs = apiFilters;
  const { data: stockHistory = [] } = useStockHistory(filterArgs);
  const { data: salesHistory = [] } = useSalesHistory(filterArgs);
  const { data: recipes = [] } = useRecipeRanking({
    ...apiFilters,
    ingredientId: recipeIngredientId || undefined,
  });
  const { data: revenueSummary } = useRevenueSummary(12, apiFilters);
  const { data: weekdayOrders = [] } = useWeekdayOrders(
    apiFilters.days,
    apiFilters,
  );

  const hour = new Date().getHours();
  const period = hour < 12 ? 'Bom dia' : hour < 18 ? 'Boa tarde' : 'Boa noite';
  const dateStr = new Date().toLocaleDateString('pt-BR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  });

  const allIngredientOptions = data?.filters.ingredients ?? [];

  async function handleDashboardExport(format: DashboardExportFormat) {
    setExportError('');
    setExportingFormat(format);
    try {
      await downloadDashboardExport(format, apiFilters, themeId);
    } catch (err) {
      setExportError(
        err instanceof Error ? err.message : 'Não foi possível exportar.',
      );
    } finally {
      setExportingFormat(null);
    }
  }

  const rankingConfig = useMemo(() => {
    if (!data) {
      return {
        rows: [] as Array<DashboardRankItem | DashboardCategoryItem>,
        label: 'Valor',
        valueTooltip: 'Valor exibido',
        entityLabel: 'Ingrediente',
      };
    }

    if (rankingKind === 'stock_ingredient') {
      return {
        rows: groupItems<DashboardUnitRankGroup>(
          rankingMode === 'top'
            ? data.top_stock_products_by_unit
            : data.bottom_stock_products_by_unit,
          rankingUnit,
        ) as DashboardRankItem[],
        label: 'Estoque atual',
        valueTooltip: 'Quantidade atual em estoque',
        entityLabel: 'Ingrediente',
      };
    }

    if (rankingKind === 'stock_category') {
      return {
        rows: groupItems<DashboardUnitCategoryGroup>(
          rankingMode === 'top'
            ? data.top_stock_categories_by_unit
            : data.bottom_stock_categories_by_unit,
          rankingUnit,
        ) as DashboardCategoryItem[],
        label: 'Estoque atual',
        valueTooltip: 'Soma do estoque atual dos ingredientes da categoria',
        entityLabel: 'Categoria',
      };
    }

    if (rankingKind === 'usage_ingredient') {
      return {
        rows: groupItems<DashboardUnitRankGroup>(
          rankingMode === 'top'
            ? data.top_output_products_by_unit
            : data.bottom_output_products_by_unit,
          rankingUnit,
        ) as DashboardRankItem[],
        label: 'Uso estimado',
        valueTooltip:
          'Uso estimado por vendas.quantity * receitas_ingredientes.qty',
        entityLabel: 'Ingrediente',
      };
    }

    return {
      rows: [] as Array<DashboardRankItem | DashboardCategoryItem>,
      label: 'Valor',
      valueTooltip: 'Valor exibido',
      entityLabel: 'Ingrediente',
    };
  }, [data, rankingKind, rankingMode, rankingUnit]);

  const categoryUsageItems = groupItems<DashboardUnitCategoryGroup>(
    categoryUsageMode === 'top'
      ? (data?.top_output_categories_by_unit ?? [])
      : (data?.bottom_output_categories_by_unit ?? []),
    categoryUsageUnit,
  ) as DashboardCategoryItem[];

  const rankingSubtitle = {
    stock_ingredient: 'Estoque por ingrediente',
    stock_category: 'Estoque por categoria',
    usage_ingredient: 'Uso por ingrediente',
    recipes: 'Receitas que mais saem',
  }[rankingKind];

  const renderTrendFilters = () =>
    data ? (
      <TrendFilters
        seriesMetrics={seriesMetrics}
        onSeriesMetricsChange={setSeriesMetrics}
      />
    ) : null;

  if (isError) {
    return (
      <div className="flex flex-col h-screen bg-surface overflow-auto">
        <div className="flex h-[73px] flex-shrink-0 items-center border-b border-stone-200 bg-white px-8">
          <div>
            <h1 className="text-xl font-semibold text-stone-900">Dashboard</h1>
            <p className="text-sm text-stone-400 mt-0.5">
              Falha ao carregar dados
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-surface overflow-auto">
      <CoffeeLoading show={isLoading || !data} />
      <DashboardFilterDrawer
        open={globalFiltersOpen}
        filters={draftFilters}
        categories={data?.filters.categories ?? []}
        months={data?.filters.months ?? []}
        onChange={setDraftFilters}
        onOpen={() => {
          setDraftFilters(globalFilters);
          setGlobalFiltersOpen(true);
        }}
        onClose={() => setGlobalFiltersOpen(false)}
        onApply={() => {
          setGlobalFilters(draftFilters);
          setGlobalFiltersOpen(false);
        }}
        onClear={() => {
          setDraftFilters(DEFAULT_GLOBAL_FILTERS);
        }}
        appliedCount={activeCount}
      />
      <div className="flex h-[73px] flex-shrink-0 items-center justify-between gap-4 border-b border-stone-200 bg-white px-8">
        <div>
          <h1 className="text-xl font-semibold text-stone-900">
            {period}, Fernanda
          </h1>
          <p className="text-sm text-stone-400 mt-0.5 capitalize">
            {dateStr} · Saltim Café
          </p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <div className="flex items-center gap-2">
            <AppSelect
              value={dashboardExportFormat}
              onChange={(value) =>
                setDashboardExportFormat((value || 'pdf') as DashboardExportFormat)
              }
              options={DASHBOARD_EXPORT_OPTIONS}
              className="w-28"
            />
            <button
              type="button"
              onClick={() => handleDashboardExport(dashboardExportFormat)}
              disabled={!data || Boolean(exportingFormat)}
              className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-3 py-2 text-xs font-bold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Download className="size-4" strokeWidth={1.9} />
              {exportingFormat ? 'Exportando...' : 'Exportar'}
            </button>
          </div>
          {exportError && (
            <span className="text-xs font-medium text-saltim-red">
              {exportError}
            </span>
          )}
        </div>
      </div>

      <div className="flex-1 p-6 lg:p-8 flex flex-col gap-6">
        {!data ? null : (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
              {data.cards.items.map((item) => (
                <StatCard key={item.id} item={item} />
              ))}
            </div>

            <Panel
              title="Estoque e vendas ao longo do tempo"
              action={
                <FilterMenu
                  open={trendFiltersOpen}
                  onToggle={() => setTrendFiltersOpen((open) => !open)}
                  onClose={() => setTrendFiltersOpen(false)}
                >
                  {renderTrendFilters()}
                </FilterMenu>
              }
            >
              <CombinedHistoryChart
                stock={stockHistory}
                sales={salesHistory}
                metrics={seriesMetrics}
              />
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
                    {data.alerts.map((alert) => (
                      <tr
                        key={alert.ingredient_id}
                        className="border-b border-stone-100 last:border-0"
                      >
                        <td className="py-3 pr-4 font-medium text-stone-900">
                          {displayName(alert.name)}
                        </td>
                        <td className="py-3 pr-4 text-stone-500">
                          {displayName(alert.category)}
                        </td>
                        <td className="py-3 pr-4 text-right tabular-nums text-stone-700">
                          {fmt.number(alert.current_qty, 2)} {alert.unit}
                        </td>
                        <td className="py-3 pr-4 text-right tabular-nums text-stone-700">
                          {fmt.number(alert.avg_daily_output, 2)} {alert.unit}
                        </td>
                        <td className="py-3 pr-4 text-right tabular-nums text-stone-700">
                          {fmt.number(alert.coverage_days, 2)} dias
                        </td>
                        <td className="py-3 pr-4 text-right tabular-nums text-stone-700">
                          {fmt.number(alert.suggested_qty, 2)} {alert.unit}
                        </td>
                        <td className="py-3">
                          <span
                            className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${severityClass(alert.severity)}`}
                          >
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

            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
              <Panel
                title="Faturamento"
                subtitle={
                  revenuePeriod === 'monthly' ? 'Por mês' : 'Por quarter'
                }
                action={
                  <FilterMenu
                    open={revenueFiltersOpen}
                    onToggle={() => setRevenueFiltersOpen((open) => !open)}
                    onClose={() => setRevenueFiltersOpen(false)}
                  >
                    <RevenueFilters
                      period={revenuePeriod}
                      onPeriodChange={setRevenuePeriod}
                    />
                  </FilterMenu>
                }
              >
                <RevenueBarChart data={revenueSummary?.[revenuePeriod] ?? []} />
              </Panel>

              <Panel
                title="Pedidos por dia da semana"
                subtitle="Últimos 90 dias"
              >
                <WeekdayOrdersBarChart data={weekdayOrders} />
              </Panel>
            </div>

            <div className="grid grid-cols-1 gap-6 2xl:grid-cols-[minmax(0,1.75fr)_minmax(320px,0.75fr)]">
              <Panel
                title="Rankings"
                subtitle={rankingSubtitle}
                action={
                  <FilterMenu
                    open={rankingFiltersOpen}
                    onToggle={() => setRankingFiltersOpen((open) => !open)}
                    onClose={() => setRankingFiltersOpen(false)}
                  >
                    <RankingFilters
                      kind={rankingKind}
                      mode={rankingMode}
                      unit={rankingUnit}
                      recipeIngredientId={recipeIngredientId}
                      ingredients={allIngredientOptions}
                      onKindChange={setRankingKind}
                      onModeChange={setRankingMode}
                      onUnitChange={setRankingUnit}
                      onRecipeIngredientChange={setRecipeIngredientId}
                    />
                  </FilterMenu>
                }
              >
                {rankingKind === 'recipes' ? (
                  <RecipeRankingTable recipes={recipes} />
                ) : (
                  <RankingTable
                    rows={rankingConfig.rows}
                    unit={rankingUnit}
                    label={rankingConfig.label}
                    valueTooltip={rankingConfig.valueTooltip}
                    entityLabel={rankingConfig.entityLabel}
                  />
                )}
              </Panel>

              <Panel
                title="Uso por categoria"
                subtitle={
                  categoryUsageMode === 'top'
                    ? 'Categorias mais utilizadas'
                    : 'Categorias menos utilizadas'
                }
                action={
                  <FilterMenu
                    open={categoryUsageFiltersOpen}
                    onToggle={() =>
                      setCategoryUsageFiltersOpen((open) => !open)
                    }
                    onClose={() => setCategoryUsageFiltersOpen(false)}
                  >
                    <CategoryUsageFilters
                      mode={categoryUsageMode}
                      unit={categoryUsageUnit}
                      onModeChange={setCategoryUsageMode}
                      onUnitChange={setCategoryUsageUnit}
                    />
                  </FilterMenu>
                }
              >
                <CategoryUsageDonutChart
                  data={categoryUsageItems}
                  unit={categoryUsageUnit}
                />
              </Panel>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
