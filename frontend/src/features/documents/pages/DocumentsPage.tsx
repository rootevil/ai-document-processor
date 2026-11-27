
import { DocumentUpload } from '../components/DocumentUpload'
import { DocumentsTable } from '../components/DocumentsTable'

import {
  useDocuments,
  useUploadDocument,
} from '../hooks/useDocuments'

export function DocumentsPage() {
  // Load the current document list through TanStack Query.
  const documentsQuery = useDocuments()

  // Manage uploads and automatic document-list refresh.
  const uploadMutation = useUploadDocument()

  const documents = documentsQuery.data ?? []

  const uploadError = uploadMutation.error instanceof Error
    ? uploadMutation.error.message
    : null

  return (
    <section className="space-y-8">
      {/* Workspace heading */}
      <div>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight text-slate-900">
              Document workspace
            </h2>

            <p className="mt-2 text-sm text-slate-600">
              Upload business documents, inspect extracted information,
              and review extraction results.
            </p>
          </div>

          <div className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-600">
            {documents.length} {documents.length === 1 ? 'document' : 'documents'}
          </div>
        </div>
      </div>

      {/* Upload area */}
      <DocumentUpload
        onUpload={(file) => uploadMutation.mutate(file)}
        isUploading={uploadMutation.isPending}
        errorMessage={uploadError}
        isSuccess={uploadMutation.isSuccess}
      />

      {/* Document list */}
      <section className="space-y-4">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">
            Your documents
          </h3>

          <p className="mt-1 text-sm text-slate-500">
            All documents uploaded to your workspace.
          </p>
        </div>

        {documentsQuery.isPending && (
          <div
            role="status"
            className="rounded-xl border border-slate-200 bg-white px-6 py-12 text-center text-sm text-slate-500"
          >
            Loading documents...
          </div>
        )}

        {documentsQuery.isError && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-5">
            <p className="text-sm font-medium text-red-800">
              Unable to load documents.
            </p>

            <p className="mt-1 text-sm text-red-700">
              {documentsQuery.error.message}
            </p>

            <button
              type="button"
              onClick={() => void documentsQuery.refetch()}
              className="mt-3 rounded-lg border border-red-300 bg-white px-3 py-2 text-sm font-medium text-red-700 hover:bg-red-100"
            >
              Try again
            </button>
          </div>
        )}

        {!documentsQuery.isPending && !documentsQuery.isError && (
          <DocumentsTable documents={documents} />
        )}
      </section>
    </section>
  )
}
