import { createRoute, useNavigate } from '@tanstack/react-router';
import { rootRoute } from './Root';
import { useEstoque, getStockStatus } from '../hooks/useEstoque';
import { CATEGORIES } from '../data/ingredients';

export const dashboardRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  component: DashboardPage,
});

function StatCard({
  value,
  label,
  color,
}: {
  value: number;
  label: string;
  color: string;
}) {
  return (
    <div className="bg-white rounded-2xl border border-stone-200 p-6">
      <div className="text-3xl font-bold tabular-nums" style={{ color }}>
        {value}
      </div>
      <div className="text-sm text-stone-500 mt-1.5">{label}</div>
    </div>
  );
}

function ActionCard({
  title,
  sub,
  icon,
  onClick,
}: {
  title: string;
  sub: string;
  icon: React.ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="w-full bg-white rounded-2xl border border-stone-200 p-5 flex items-center justify-between hover:border-brand-600 hover:shadow-sm transition-all text-left group"
    >
      <div>
        <div className="text-sm font-semibold text-stone-900">{title}</div>
        <div className="text-xs text-stone-400 mt-1">{sub}</div>
      </div>
      <div className="size-10 rounded-xl bg-brand-50 flex items-center justify-center ml-4 group-hover:bg-brand-600 transition-colors">
        <span className="text-brand-600 group-hover:text-white transition-colors">
          {icon}
        </span>
      </div>
    </button>
  );
}

export function DashboardPage() {
  const navigate = useNavigate();
  const { data: stock = [] } = useEstoque();

  const hour = new Date().getHours();
  const period = hour < 12 ? 'Bom dia' : hour < 18 ? 'Boa tarde' : 'Boa noite';
  const dateStr = new Date().toLocaleDateString('pt-BR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  });

  const total = stock.length;
  const ok = stock.filter((i) => getStockStatus(i) === 'OK').length;
  const atencao = stock.filter((i) => getStockStatus(i) === 'Atenção').length;
  const critico = stock.filter((i) => getStockStatus(i) === 'Crítico').length;
  const esgotado = stock.filter((i) => getStockStatus(i) === 'Esgotado').length;

  return (
    <div className="flex flex-col h-screen bg-surface overflow-auto">
      <div className="bg-white border-b border-stone-200 px-8 py-5 flex-shrink-0">
        <h1 className="text-xl font-semibold text-stone-900">
          {period}, Fernanda 👋
        </h1>
        <p className="text-sm text-stone-400 mt-0.5 capitalize">
          {dateStr} · Saltim Café
        </p>
      </div>

      <div className="flex-1 p-8 flex flex-col gap-6">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard value={total} label="Insumos" color="#1A1917" />
          <StatCard value={ok} label="Em estoque OK" color="#2D7A3A" />
          <StatCard value={atencao} label="Em atenção" color="#F07820" />
          <StatCard
            value={critico + esgotado}
            label="Críticos / esgotados"
            color="#E4332B"
          />
        </div>
      </div>
    </div>
  );
}
