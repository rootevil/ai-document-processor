import { DocumentDetailsPage } from '../../features/documents/pages/DocumentDetailsPage'
import {
  BrowserRouter,
  Route,
  Routes,
} from 'react-router-dom'

import { AppLayout } from '../../components/layout/AppLayout'
import { DocumentsPage } from '../../features/documents/pages/DocumentsPage'

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<DocumentsPage />} />
          <Route
            path="documents/:documentId"
            element={<DocumentDetailsPage />}
          />
          <Route
            path="*"
            element={
              <div className="py-12 text-center">
                <h2 className="text-xl font-semibold">
                  Page not found
                </h2>
                <p className="mt-2 text-sm text-slate-500">
                  The requested page does not exist.
                </p>
              </div>
            }
          />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
