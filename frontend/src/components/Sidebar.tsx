import { Link } from '@tanstack/react-router'

function HomeIcon() {
  return (
    <svg viewBox="0 0 20 20" className="size-4.5 flex-shrink-0" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 9.5L10 3l7 6.5V17a1 1 0 01-1 1H4a1 1 0 01-1-1V9.5z" />
      <path d="M7 18v-6h6v6" />
    </svg>
  )
}

function PackageIcon() {
  return (
    <svg viewBox="0 0 20 20" className="size-4.5 flex-shrink-0" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="7" width="16" height="11" rx="1" />
      <path d="M5 7V5a5 5 0 0110 0v2" />
    </svg>
  )
}

interface NavItemProps {
  to: string
  icon: React.ReactNode
  label: string
}

function NavItem({ to, icon, label }: NavItemProps) {
  return (
    <Link
      to={to}
      className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-white/40 hover:text-white hover:bg-white/8 transition-colors"
      activeProps={{ className: 'flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-brand-600 bg-brand-600/15' }}
      activeOptions={{ exact: to === '/' }}
    >
      {icon}
      {label}
    </Link>
  )
}

export function Sidebar() {
  return (
    <aside className="w-56 bg-saltim-dark flex flex-col flex-shrink-0">
      {/* Brand */}
      <div className="px-5 py-5 border-b border-white/8">
        <div className="flex items-center gap-2.5">
          <div className="size-7 rounded-lg bg-brand-600 flex items-center justify-center flex-shrink-0">
            <span className="text-white text-xs font-black leading-none">S</span>
          </div>
          <span className="text-base font-bold text-saltim-cream tracking-tight">Saltim Café</span>
        </div>
      </div>
      <nav className="flex flex-col gap-1 p-3 pt-4">
        <NavItem to="/"        icon={<HomeIcon />}    label="Início" />
        <NavItem to="/estoque" icon={<PackageIcon />} label="Estoque" />
      </nav>
    </aside>
  )
}
