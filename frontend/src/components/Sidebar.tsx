import { Link } from '@tanstack/react-router';
import {
  Activity,
  ClipboardList,
  LayoutDashboard,
  Package,
  PackageCheck,
  Palette,
  ReceiptText,
  ShoppingCart,
  Truck,
} from 'lucide-react';
import type { ComponentType } from 'react';

interface NavItemProps {
  to: string;
  icon: ComponentType<{ className?: string; strokeWidth?: number }>;
  label: string;
  exact?: boolean;
}

function SaltimLogo() {
  return (
    <span
      aria-label="Saltim"
      role="img"
      className="size-8"
      style={{
        backgroundColor: 'var(--theme-logo)',
        mask: 'url(/images/maestro-logo.svg) center / contain no-repeat',
        WebkitMask: 'url(/images/maestro-logo.svg) center / contain no-repeat',
      }}
    />
  );
}

function NavItem({ to, icon: Icon, label, exact }: NavItemProps) {
  return (
    <Link
      to={to}
      className="saltim-sidebar-item group/item relative flex size-11 items-center justify-center rounded-xl text-sm font-semibold transition-colors"
      activeProps={{ className: 'text-brand-700 bg-brand-50' }}
      inactiveProps={{
        className: 'text-stone-500 hover:text-brand-700 hover:bg-brand-50',
      }}
      activeOptions={{ exact }}
      aria-label={label}
    >
      <span className="flex size-6 flex-shrink-0 items-center justify-center">
        <Icon className="size-5 shrink-0" strokeWidth={1.9} />
      </span>
      <span className="saltim-sidebar-tooltip pointer-events-none absolute left-[calc(100%+10px)] top-1/2 z-50 -translate-y-1/2 whitespace-nowrap rounded-lg border border-stone-200 bg-brand-50 px-3 py-2 text-xs font-bold text-brand-700 opacity-0 transition-opacity group-hover/item:opacity-100">
        {label}
      </span>
    </Link>
  );
}

export function Sidebar() {
  return (
    <aside className="saltim-sidebar h-screen w-[72px] bg-white border-r border-stone-200 flex flex-col flex-shrink-0 overflow-visible">
      {/* Hover expansion intentionally disabled for now.
          Previous classes: group/sidebar hover:w-56 transition-[width] duration-200 */}
      <div className="h-[73px] w-[72px] border-b border-stone-100 bg-[#232323] flex items-center justify-start pl-[1.2rem]">
        <SaltimLogo />
      </div>
      <nav className="flex flex-col items-center gap-2 p-3 pt-5">
        <NavItem to="/" icon={LayoutDashboard} label="Dashboard" exact />
        <NavItem to="/estoque" icon={Package} label="Estoque" exact />
        <NavItem to="/fornecedores" icon={Truck} label="Fornecedores" />
        <NavItem to="/pedidos" icon={PackageCheck} label="Pedidos" />
        <NavItem to="/vendas" icon={ReceiptText} label="Vendas" />
        <NavItem to="/compras/planejamento" icon={ShoppingCart} label="Compras" />
        <NavItem to="/estoque/contagem" icon={ClipboardList} label="Contagem" />
        <NavItem to="/ml/criticidade" icon={Activity} label="Criticidade" />
        <NavItem
          to="/configuracoes/aparencia"
          icon={Palette}
          label="Aparência"
        />
      </nav>
    </aside>
  );
}
