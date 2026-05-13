import { useState, useMemo } from 'react';
import { createRoute, useNavigate } from '@tanstack/react-router';
import { rootRoute } from './Root';
import { useEstoque, useAtualizarEstoque } from '../hooks/useEstoque';
import {
  useContagem,
  getGlobalProgress,
  buildAllUpdates,
  initializeAll,
} from '../hooks/useContagem';
import { CATEGORIES, type Category } from '../data/ingredients';
import { cn } from '../lib/cn';

export const contagemCategoriaRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/estoque/contagem/$index',
  component: ContagemCategoriaPage,
});

// Emoji fallback per category (used when image fails to load)
const CATEGORY_EMOJI: Record<Category, string> = {
  Laticínios: '🥛',
  Proteínas: '🥩',
  'Grãos, Farinhas e Massas': '🌾',
  'Açúcares e Mel': '🍯',
  'Chocolates e Cacau': '🍫',
  'Nozes e Sementes': '🌰',
  'Frutas Frescas': '🍓',
  'Frutas Secas e Congeladas': '🍒',
  'Legumes e Verduras': '🥦',
  'Temperos e Especiarias': '🧂',
  'Óleos e Gorduras': '🫒',
  'Molhos e Condimentos': '🫙',
  'Bebidas e Bases': '☕',
  'Semi-prontos e Preparados': '🥘',
};

// Per-category Unsplash keywords for food photography
const CATEGORY_SEARCH: Record<Category, string> = {
  Laticínios: 'dairy,cream,milk,butter',
  Proteínas: 'eggs,meat,chicken,protein',
  'Grãos, Farinhas e Massas': 'flour,pasta,bread,grain',
  'Açúcares e Mel': 'honey,sugar,sweet',
  'Chocolates e Cacau': 'chocolate,cocoa,dark+chocolate',
  'Nozes e Sementes': 'nuts,almonds,seeds,walnut',
  'Frutas Frescas': 'fresh,fruit,strawberry,tropical',
  'Frutas Secas e Congeladas': 'berry,frozen,dried,fruit',
  'Legumes e Verduras': 'vegetables,greens,salad',
  'Temperos e Especiarias': 'spices,herbs,cinnamon,pepper',
  'Óleos e Gorduras': 'olive,oil,cooking',
  'Molhos e Condimentos': 'sauce,condiment,ketchup',
  'Bebidas e Bases': 'coffee,espresso,drink',
  'Semi-prontos e Preparados': 'food,kitchen,cooking,meal',
};

function getStep(unit: string): number {
  return ['KG', 'G', 'GR', 'L', 'LT', 'ML'].includes(unit.toUpperCase())
    ? 0.1
    : 1;
}

function fmtQty(qty: number, unit: string): string {
  const step = getStep(unit);
  const n = step < 1 ? qty.toFixed(1) : String(Math.round(qty));
  return `${n} ${unit}`;
}

function GlobalProgressBar({
  touched,
  total,
}: {
  touched: number;
  total: number;
}) {
  const pct = total === 0 ? 0 : Math.round((touched / total) * 100);
  const done = pct === 100;
  return (
    <div className="bg-white border border-stone-200 rounded-xl p-4">
      <div className="flex items-center justify-between mb-2.5">
        <span
          className={cn(
            'text-xs font-medium',
            done ? 'text-green-700' : 'text-stone-500',
          )}
        >
          {done ? 'Estoque completo! ✓' : 'Progresso total do estoque'}
        </span>
        <span className="text-xs tabular-nums text-stone-500">
          <span className="font-bold text-stone-900">{touched}</span>
          {' / '}
          {total}
          <span
            className={cn(
              'ml-1',
              done ? 'text-green-700 font-bold' : 'text-stone-400',
            )}
          >
            · {pct}%
          </span>
        </span>
      </div>
      <div className="h-1.5 bg-stone-100 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-300"
          style={{
            width: `${pct}%`,
            backgroundColor: done ? '#2D7A3A' : '#F07820',
          }}
        />
      </div>
    </div>
  );
}

function ProductImage({
  name,
  category,
}: {
  name: string;
  category: Category;
}) {
  const [failed, setFailed] = useState(false);
  const emoji = CATEGORY_EMOJI[category] ?? '📦';
  // Search by item name first; Unsplash will fall back to a food photo if no match
  const query = CATEGORY_SEARCH[category] ?? 'food';

  if (failed) {
    return (
      <div className="size-14 rounded-xl bg-stone-50 border border-stone-100 flex items-center justify-center text-2xl select-none flex-shrink-0">
        {emoji}
      </div>
    );
  }

  return (
    <img
      src={`https://source.unsplash.com/80x80/?${encodeURIComponent(name.toLowerCase())},${query}`}
      alt=""
      className="size-14 rounded-xl object-cover flex-shrink-0 bg-stone-100"
      loading="lazy"
      onError={() => setFailed(true)}
    />
  );
}

export function ContagemCategoriaPage() {
  const navigate = useNavigate();
  const { index } = contagemCategoriaRoute.useParams();
  const categoryIndex = parseInt(index);
  const category = CATEGORIES[categoryIndex];

  const { data: stock = [] } = useEstoque();
  const atualizar = useAtualizarEstoque();

  // Garante que o progresso global esteja correto mesmo entrando direto na categoria
  initializeAll(stock);

  const items = useMemo(
    () => stock.filter((i) => i.category === category),
    [stock, category],
  );

  const {
    adjust,
    setCount,
    confirmar,
    desmarcar,
    marcarTodos,
    getCount,
    isTouched,
    touchedCount,
    totalCount,
    buildUpdates,
  } = useContagem(items);

  function toggleContado(id: number) {
    if (isTouched(id)) desmarcar(id);
    else confirmar(id);
  }
  const globalProgress = getGlobalProgress(stock);

  const [search, setSearch] = useState('');

  const visible = useMemo(
    () =>
      !search
        ? items
        : items.filter((i) =>
            i.name.toLowerCase().includes(search.toLowerCase()),
          ),
    [items, search],
  );

  const isCategoryDone = touchedCount === totalCount && totalCount > 0;
  const isGlobalDone =
    globalProgress.touchedCount === globalProgress.totalCount &&
    globalProgress.totalCount > 0;
  const isLastCategory = categoryIndex === CATEGORIES.length - 1;

  async function handleNext() {
    const updates = buildUpdates();
    if (updates.size > 0) await atualizar.mutateAsync(updates);
    if (isGlobalDone || isLastCategory) {
      navigate({ to: '/estoque', search: { counted: 'Contagem finalizada' } });
    } else {
      navigate({
        to: '/estoque/contagem/$index',
        params: { index: String(categoryIndex + 1) },
      });
    }
  }

  async function handleSairESalvar() {
    const updates = buildAllUpdates(stock);
    if (updates.size > 0) await atualizar.mutateAsync(updates);
    navigate({ to: '/estoque', search: {} });
  }

  if (!category) {
    return <div className="p-8 text-stone-400">Categoria não encontrada.</div>;
  }

  const remaining = totalCount - touchedCount;

  let buttonLabel: string;
  if (atualizar.isPending) {
    buttonLabel = 'Salvando…';
  } else if (isGlobalDone) {
    buttonLabel = 'Finalizar contagem';
  } else if (isCategoryDone && !isLastCategory) {
    buttonLabel = `Próxima: ${CATEGORIES[categoryIndex + 1]} →`;
  } else if (isLastCategory) {
    buttonLabel = 'Finalizar contagem';
  } else {
    buttonLabel = `Salvar e continuar → (${remaining} restante${remaining !== 1 ? 's' : ''})`;
  }

  return (
    <div className="flex flex-col h-screen bg-surface">
      {/* Header */}
      <div className="bg-white border-b border-stone-200 px-8 py-4 flex items-center gap-3 flex-shrink-0">
        <button
          onClick={() => navigate({ to: '/estoque/contagem' })}
          className="size-8 rounded-lg border border-stone-200 flex items-center justify-center hover:bg-stone-50 transition-colors flex-shrink-0"
        >
          <svg
            viewBox="0 0 20 20"
            className="size-4 text-stone-400"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="12 4 4 10 12 16" />
          </svg>
        </button>
        <div className="flex-1 min-w-0">
          <p className="text-xs text-stone-400 font-medium uppercase tracking-wide">
            {category}
          </p>
          <h1 className="text-lg font-semibold text-stone-900 leading-tight">
            Contagem de insumos
          </h1>
        </div>
        <div className="flex items-center gap-4 flex-shrink-0">
          <span className="text-xs text-stone-500 tabular-nums">
            {touchedCount} / {totalCount}
          </span>
          <button
            onClick={handleSairESalvar}
            disabled={atualizar.isPending}
            className="text-xs text-stone-400 hover:text-stone-700 transition-colors font-medium disabled:opacity-40"
          >
            Salvar e sair
          </button>
        </div>
      </div>

      {/* Subheader */}
      <div className="px-8 py-4 flex flex-col gap-3 bg-surface flex-shrink-0">
        <GlobalProgressBar
          touched={globalProgress.touchedCount}
          total={globalProgress.totalCount}
        />
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <svg
              viewBox="0 0 20 20"
              className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-stone-400 pointer-events-none"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="9" cy="9" r="6" />
              <line x1="13.5" y1="13.5" x2="18" y2="18" />
            </svg>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar item…"
              className="w-full pl-9 pr-4 py-2 text-sm border border-stone-200 rounded-lg bg-white outline-none focus:ring-2 focus:ring-brand-600/20 focus:border-brand-600 transition"
            />
          </div>
          <button
            onClick={marcarTodos}
            className="flex-shrink-0 px-3 py-2 text-xs font-semibold rounded-lg transition-colors whitespace-nowrap cursor-pointer text-white"
            style={{ backgroundColor: '#52B9EB' }}
          >
            Marcar todos
          </button>
        </div>
      </div>

      {/* Item grid */}
      <div className="flex-1 overflow-auto px-8 pb-6">
        <div className="grid grid-cols-2 gap-3 pt-1">
          {visible.map((item) => (
            <ItemCard
              key={item.id}
              item={item}
              value={getCount(item.id)}
              onAdjust={adjust}
              onSet={setCount}
              onToggle={toggleContado}
              done={isTouched(item.id)}
            />
          ))}
        </div>
      </div>

      {/* Bottom bar */}
      <div className="bg-white border-t border-stone-200 px-8 py-4 flex-shrink-0">
        <button
          onClick={handleNext}
          disabled={atualizar.isPending}
          className="w-full py-3 rounded-xl text-sm font-semibold transition-colors disabled:opacity-60 bg-brand-600 text-white hover:bg-brand-700"
        >
          {buttonLabel}
        </button>
      </div>
    </div>
  );
}

interface ItemCardProps {
  item: {
    id: number;
    name: string;
    unit: string;
    minQty: number;
    currentQty: number;
    category: Category;
  };
  value: number;
  onAdjust: (id: number, delta: number) => void;
  onSet: (id: number, value: number) => void;
  onToggle: (id: number) => void;
  done: boolean;
}

function ItemCard({
  item,
  value,
  onAdjust,
  onSet,
  onToggle,
  done,
}: ItemCardProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState('');

  const isCritical = done && value < item.minQty;
  const step = getStep(item.unit);

  // Deficit: how far below minimum (based on counted value when counted, else current stock)
  const effectiveQty = done ? value : item.currentQty;
  const deficit = Math.round((item.minQty - effectiveQty) * 100) / 100;

  function startEdit() {
    setDraft(value === 0 ? '' : String(value));
    setEditing(true);
  }

  function commitEdit() {
    const num = parseFloat(draft);
    onSet(item.id, isNaN(num) ? 0 : num);
    setEditing(false);
  }

  return (
    <div
      className={cn(
        'rounded-xl border p-4 flex flex-col gap-3 transition-colors',
        done
          ? isCritical
            ? 'bg-red-50 border-red-300'
            : 'bg-brand-50 border-brand-300'
          : 'bg-white border-stone-200',
      )}
    >
      {/* Image + name + checkbox */}
      <div className="flex items-start gap-2.5">
        <ProductImage name={item.name} category={item.category} />
        <div className="flex-1 min-w-0">
          <div className="text-sm font-semibold text-stone-900 leading-snug line-clamp-2">
            {item.name}
          </div>
          {isCritical && done && (
            <span className="inline-flex items-center gap-1 mt-1 text-xs font-semibold text-red-600">
              Crítico
            </span>
          )}
        </div>
        <button
          onClick={() => onToggle(item.id)}
          className={cn(
            'size-5 rounded flex-shrink-0 border-2 flex items-center justify-center transition-colors mt-0.5 cursor-pointer',
            done
              ? isCritical
                ? 'bg-red-500 border-red-500'
                : 'bg-brand-600 border-brand-600'
              : 'border-stone-300 bg-white hover:border-brand-600',
          )}
          title={done ? 'Desmarcar' : 'Marcar como contado'}
        >
          {done && (
            <svg
              viewBox="0 0 12 12"
              className="size-3 text-white"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="2 6 5 9 10 3" />
            </svg>
          )}
        </button>
      </div>

      {/* Qty info */}
      <div className="text-xs space-y-0.5">
        <div className="flex items-baseline gap-1">
          <span className="text-stone-400">Atual</span>
          <span className="font-bold text-stone-800">
            {fmtQty(item.currentQty, item.unit)}
          </span>
        </div>
        <div className="flex items-baseline gap-1">
          <span className="text-stone-400">Mín</span>
          <span className="text-stone-500">
            {fmtQty(item.minQty, item.unit)}
          </span>
        </div>
        {deficit > 0 && (
          <div className="text-amber-600 font-semibold pt-0.5">
            +{fmtQty(deficit, item.unit)} para o mínimo
          </div>
        )}
      </div>

      {/* Stepper — right-aligned */}
      <div className="flex items-center justify-end gap-1.5 mt-auto">
        <div className="flex items-center bg-stone-100 rounded-lg border border-stone-200 overflow-hidden">
          <button
            onClick={() => onAdjust(item.id, -step)}
            className="w-7 h-8 flex items-center justify-center text-stone-500 hover:text-brand-600 text-base font-medium transition-colors cursor-pointer"
          >
            −
          </button>

          {editing ? (
            <input
              autoFocus
              type="number"
              min="0"
              step={step}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onBlur={commitEdit}
              onKeyDown={(e) =>
                e.key === 'Enter' && (e.target as HTMLInputElement).blur()
              }
              className="w-14 h-8 text-center text-sm font-bold text-stone-900 bg-white outline-none border-0 tabular-nums [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
            />
          ) : (
            <button
              onClick={startEdit}
              className="w-14 h-8 flex items-center justify-center text-sm font-bold text-stone-900 tabular-nums hover:bg-white transition-colors"
              title="Toque para digitar"
            >
              {value % 1 === 0 ? value : value.toFixed(1)}
            </button>
          )}

          <button
            onClick={() => onAdjust(item.id, step)}
            className="w-7 h-8 flex items-center justify-center text-stone-500 hover:text-brand-600 text-base font-medium transition-colors cursor-pointer"
          >
            +
          </button>
        </div>
        <span className="text-xs font-bold text-stone-400 uppercase tracking-wider w-6 text-right">
          {item.unit}
        </span>
      </div>
    </div>
  );
}
