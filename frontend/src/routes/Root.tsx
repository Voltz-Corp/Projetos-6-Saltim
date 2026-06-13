import { createRootRoute, Outlet, useRouterState } from '@tanstack/react-router'
import { AgentChatWidget } from '../components/AgentChatWidget'
import { Sidebar } from '../components/Sidebar'
import { VLibrasWidget } from '../components/VLibrasWidget'

export const rootRoute = createRootRoute({
  component: Root,
})

function Root() {
  const pathname = useRouterState({ select: state => state.location.pathname })
  const isSalesApp = pathname.startsWith('/vendas')

  if (isSalesApp) {
    return (
      <div className="min-h-screen bg-surface">
        <Outlet />
        <AgentChatWidget />
        <VLibrasWidget />
      </div>
    )
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col min-h-screen overflow-hidden">
        <Outlet />
      </div>
      <AgentChatWidget />
      <VLibrasWidget />
    </div>
  )
}
