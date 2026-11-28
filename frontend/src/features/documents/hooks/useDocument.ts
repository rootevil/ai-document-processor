import { useQuery } from '@tanstack/react-query'

import { getDocument } from '../../../lib/api/documentsApi'

// Each document has its own cache entry.
export function useDocument(documentId: string) {
  return useQuery({
    queryKey: ['documents', documentId],

    // The API client validates the returned document with Zod.
    queryFn: ({ signal }) => getDocument(documentId, signal),

    // Do not send a request without a valid document ID.
    enabled: documentId.length > 0,
  })
}
