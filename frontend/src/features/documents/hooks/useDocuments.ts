
import {
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'

import {
  listDocuments,
  uploadDocument,
} from '../../../lib/api/documentsApi'

// A shared query key keeps document-list caching consistent
// wherever the document workspace uses it.
export const DOCUMENTS_QUERY_KEY = ['documents'] as const

/**
 * Retrieve uploaded documents.
 *
 * TanStack Query manages loading, error, caching and refetching.
 * The supplied AbortSignal allows an obsolete request to be cancelled.
 */
export function useDocuments() {
  return useQuery({
    queryKey: DOCUMENTS_QUERY_KEY,
    queryFn: ({ signal }) => listDocuments(signal),
  })
}

/**
 * Upload a document and refresh the document list after success.
 *
 * Keeping this behavior in a hook means UI components do not
 * need to know how API caching and invalidation work.
 */
export function useUploadDocument() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (file: File) => uploadDocument(file),

    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: DOCUMENTS_QUERY_KEY,
      })
    },
  })
}
