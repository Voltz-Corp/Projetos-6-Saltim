import { createRootRoute, Outlet } from '@tanstack/react-router'
import { Sidebar } from '../components/Sidebar'

export const rootRoute = createRootRoute({
  component: Root,
})

function Root() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col min-h-screen overflow-hidden">
        <Outlet />
      </div>
    </div>
  )
}
