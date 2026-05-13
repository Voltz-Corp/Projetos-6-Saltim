import { createRouter } from '@tanstack/react-router'
import { rootRoute } from './routes/Root'
import { dashboardRoute } from './routes/DashboardPage'
import { estoqueRoute } from './routes/EstoquePage'
import { contagemRoute } from './routes/ContagemPage'
import { contagemCategoriaRoute } from './routes/ContagemCategoriaPage'

const routeTree = rootRoute.addChildren([
  dashboardRoute,
  estoqueRoute,
  contagemRoute,
  contagemCategoriaRoute,
])

export const router = createRouter({ routeTree })

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}
