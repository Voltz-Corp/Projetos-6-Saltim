import { createRouter } from '@tanstack/react-router'
import { rootRoute } from './routes/Root'
import { dashboardRoute } from './routes/DashboardPage'
import { estoqueRoute } from './routes/EstoquePage'
import { contagemRoute } from './routes/ContagemPage'
import { contagemAtualRoute } from './routes/ContagemAtualPage'
import { contagemCategoriaRoute } from './routes/ContagemCategoriaPage'
import { contagemHistoricoDetalheRoute } from './routes/ContagemHistoricoDetalhePage'
import { criticidadeRoute } from './routes/CriticidadePage'
import { ingredienteEditRoute } from './routes/IngredienteEditPage'
import { fornecedorNewRoute } from './routes/FornecedorNewPage'
import { fornecedorProfileRoute, fornecedoresRoute } from './routes/FornecedoresPage'
import { pedidoGroupDetailRoute, pedidoNewRoute, pedidosRoute } from './routes/PedidosPage'
import { vendasRoute } from './routes/VendasPage'
import { aparenciaAliasRoute, aparenciaRoute } from './routes/AparenciaPage'
import { comprasPlanejamentoRoute } from './routes/ComprasPlanejamentoPage'

const routeTree = rootRoute.addChildren([
  dashboardRoute,
  estoqueRoute,
  contagemRoute,
  contagemAtualRoute,
  contagemCategoriaRoute,
  contagemHistoricoDetalheRoute,
  criticidadeRoute,
  ingredienteEditRoute,
  fornecedoresRoute,
  fornecedorNewRoute,
  fornecedorProfileRoute,
  pedidosRoute,
  pedidoNewRoute,
  pedidoGroupDetailRoute,
  vendasRoute,
  comprasPlanejamentoRoute,
  aparenciaRoute,
  aparenciaAliasRoute,
])

export const router = createRouter({ routeTree })

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}
