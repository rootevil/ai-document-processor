import { useQuery } from '@tanstack/react-query'

import { getProcessingResult } from '../../../lib/api/documentsApi'
import { ApiError } from '../../../lib/api/apiErrors'

import type { ProcessingResultResponse } from '../../../types/document'

// Keep the query key in one place so other hooks can invalidate it.
export const PROCESSING_RESULT_QUERY_KEY = (
  documentId: string,
) => ['documents', documentId, 'processing-result'] as const

/**
 * Retrieves the most recently saved extraction result.
 *
 * A 404 means the document has not been processed yet.
 * We represent that expected state as null rather than an error.
 *
 * All other API errors are allowed to reach the UI.
 */
export function useProcessingResult(documentId: string) {
  return useQuery<ProcessingResultResponse | null, Error>({
    queryKey: PROCESSING_RESULT_QUERY_KEY(documentId),

    queryFn: async ({ signal }) => {
      try {
        return await getProcessingResult(documentId, signal)
      } catch (error) {
        // No saved result is a normal state for a new document.
        if (error instanceof ApiError && error.status === 404) {
          return null
        }

        throw error
      }
    },

    enabled: documentId.length > 0,

    // The query function handles the expected 404 itself.
    retry: false,
  })
}