import { useQuery } from '@tanstack/react-query'

import { getProcessingHistory } from '../../../lib/api/documentsApi'

/**
 * Retrieves every processing attempt for a document.
 *
 * The history includes successful and failed attempts.
 * It is read-only: this hook never changes extraction data.
 */
export function useProcessingHistory(documentId: string) {
  return useQuery({
    queryKey: ['documents', documentId, 'processing-history'],

    queryFn: ({ signal }) => getProcessingHistory(documentId, signal),

    // Do not request history until a document ID is available.
    enabled: documentId.length > 0,
  })
}