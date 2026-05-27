import { createRouter } from '@tanstack/react-router'
import { rootRoute } from './routes/Root'
import { dashboardRoute } from './routes/DashboardPage'
import { estoqueRoute } from './routes/EstoquePage'
import { contagemRoute } from './routes/ContagemPage'
import { contagemCategoriaRoute } from './routes/ContagemCategoriaPage'
import { ingredienteEditRoute } from './routes/IngredienteEditPage'
import { fornecedorNewRoute } from './routes/FornecedorNewPage'
import { fornecedorProfileRoute, fornecedoresRoute } from './routes/FornecedoresPage'
import { pedidoDetailRoute, pedidosRoute } from './routes/PedidosPage'

const routeTree = rootRoute.addChildren([
  dashboardRoute,
  estoqueRoute,
  contagemRoute,
  contagemCategoriaRoute,
  ingredienteEditRoute,
  fornecedoresRoute,
  fornecedorNewRoute,
  fornecedorProfileRoute,
  pedidosRoute,
  pedidoDetailRoute,
])

export const router = createRouter({ routeTree })

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}
