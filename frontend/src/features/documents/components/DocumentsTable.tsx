
import { FileText } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { DocumentRecord } from '../../../types/document'

interface DocumentsTableProps {
  documents: DocumentRecord[]
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`
  }

  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`
  }

  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

function formatUploadDate(value: string): string {
  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return value
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

function getStatusClasses(status: string): string {
  switch (status.toLowerCase()) {
    case 'completed':
    case 'processed':
      return 'bg-green-100 text-green-700'

    case 'processing':
      return 'bg-blue-100 text-blue-700'

    case 'failed':
    case 'error':
      return 'bg-red-100 text-red-700'

    case 'uploaded':
      return 'bg-slate-100 text-slate-700'

    default:
      return 'bg-amber-100 text-amber-700'
  }
}

/**
 * Displays the documents returned by the backend.
 *
 * This component is intentionally presentation-only.
 * Document fetching and upload behavior belong to the page and hooks.
 */
export function DocumentsTable({
  documents,
}: DocumentsTableProps) {
  if (documents.length === 0) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white px-6 py-12 text-center">
        <FileText
          aria-hidden="true"
          className="mx-auto h-10 w-10 text-slate-400"
        />

        <h3 className="mt-4 text-sm font-semibold text-slate-900">
          No documents uploaded yet
        </h3>

        <p className="mt-1 text-sm text-slate-500">
          Upload your first document to get started.
        </p>
      </div>
    )
  }

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[720px] divide-y divide-slate-200 text-left">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-5 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Document
              </th>

              <th className="px-5 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Type
              </th>

              <th className="px-5 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Size
              </th>

              <th className="px-5 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Uploaded
              </th>

              <th className="px-5 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Status
              </th>
            </tr>
          </thead>

          <tbody className="divide-y divide-slate-100">
            {documents.map((document) => (
              <tr
                key={document.id}
                className="hover:bg-slate-50"
              >
                <td className="px-5 py-4">
                  <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-600">
                      <FileText
                        aria-hidden="true"
                        className="h-5 w-5"
                      />
                    </div>

                    <Link
                      to={`/documents/${encodeURIComponent(document.id)}`}
                      className="max-w-xs truncate text-sm font-medium text-slate-900 hover:text-blue-700 hover:underline"
                    >
                      {document.original_filename}
                    </Link>

                  </div>
                </td>

                <td className="px-5 py-4 text-sm uppercase text-slate-600">
                  {document.original_filename.split('.').pop() ?? '—'}
                </td>

                <td className="px-5 py-4 text-sm text-slate-600">
                  {formatFileSize(document.file_size)}
                </td>

                <td className="px-5 py-4 text-sm text-slate-600">
                  <time dateTime={document.uploaded_at}>
                    {formatUploadDate(document.uploaded_at)}
                  </time>
                </td>

                <td className="px-5 py-4">
                  <span
                    className={[
                      'inline-flex rounded-full px-2.5 py-1 text-xs font-medium',
                      getStatusClasses(document.status),
                    ].join(' ')}
                  >
                    {document.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
