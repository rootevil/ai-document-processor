import { Outlet } from 'react-router-dom'

export function AppLayout() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      {/* Shared application header */}
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center px-6 py-4">
          <div>
            <h1 className="text-xl font-semibold tracking-tight">
              Document AI
            </h1>

            <p className="text-sm text-slate-500">
              Intelligent document processing and review
            </p>
          </div>
        </div>
      </header>

      {/* The active route renders inside this area */}
      <main className="mx-auto max-w-7xl px-6 py-8">
        <Outlet />
      </main>
    </div>
  )
}
