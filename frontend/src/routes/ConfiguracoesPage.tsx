import { Link, createRoute } from '@tanstack/react-router'
import { Palette, Settings, SlidersHorizontal, Utensils } from 'lucide-react'
import { rootRoute } from './Root'

export const configuracoesRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/configuracoes',
  component: ConfiguracoesPage,
})

function ConfiguracoesPage() {
  return (
    <div className="flex h-screen flex-col bg-surface">
      <header className="flex h-[73px] flex-shrink-0 items-center justify-between gap-4 border-b border-stone-200 bg-white px-8">
        <div>
          <p className="text-xs font-bold uppercase tracking-wide text-brand-600">
            Sistema
          </p>
          <h1 className="text-xl font-semibold text-stone-900">
            Configurações
          </h1>
        </div>
        <div className="hidden items-center gap-2 rounded-lg border border-stone-200 bg-stone-50 px-3 py-2 text-xs font-bold text-stone-600 sm:flex">
          <Settings className="size-4 text-brand-600" strokeWidth={2} />
          Preferências do Saltim
        </div>
      </header>

      <main className="flex-1 overflow-auto p-6">
        <div className="mx-auto grid max-w-5xl gap-4 md:grid-cols-2 xl:grid-cols-3">
          <SettingsCard
            to="/configuracoes/aparencia"
            icon={Palette}
            title="Temas"
            description="Ajuste modo claro ou escuro e escolha a identidade visual do sistema."
          />
          <SettingsCard
            to="/vendas"
            icon={Utensils}
            title="Visão de vendas"
            description="Abra a experiência de mesas, comandas, histórico e fechamento do dia."
          />
          <section className="rounded-lg border border-dashed border-stone-200 bg-white p-5">
            <div className="flex size-10 items-center justify-center rounded-lg bg-stone-100 text-stone-500">
              <SlidersHorizontal className="size-5" strokeWidth={2} />
            </div>
            <h2 className="mt-4 text-base font-black text-stone-900">
              Outras configurações
            </h2>
            <p className="mt-2 text-sm font-medium leading-6 text-stone-500">
              Espaço reservado para preferências operacionais, integrações e parâmetros do sistema.
            </p>
          </section>
        </div>
      </main>
    </div>
  )
}

function SettingsCard({
  to,
  icon: Icon,
  title,
  description,
}: {
  to: string
  icon: typeof Palette
  title: string
  description: string
}) {
  return (
    <Link
      to={to}
      className="group rounded-lg border border-stone-200 bg-white p-5 transition hover:border-brand-200 hover:bg-brand-50"
    >
      <div className="flex size-10 items-center justify-center rounded-lg bg-brand-50 text-brand-700 transition group-hover:bg-white">
        <Icon className="size-5" strokeWidth={2} />
      </div>
      <h2 className="mt-4 text-base font-black text-stone-900">
        {title}
      </h2>
      <p className="mt-2 text-sm font-medium leading-6 text-stone-500">
        {description}
      </p>
    </Link>
  )
}
