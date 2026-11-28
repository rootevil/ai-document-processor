import { useMutation, useQueryClient } from "@tanstack/react-query";

import { processDocument } from "../../../lib/api/documentsApi";

import { DOCUMENTS_QUERY_KEY } from "./useDocuments";
import { PROCESSING_RESULT_QUERY_KEY } from "./useProcessingResult";

import type { ProcessDocumentResponse } from "../../../types/document";

/**
 * Starts a processing attempt for one uploaded document.
 *
 * Refreshes document status, processing history, and the
 * document workspace after every attempt, including failures.
 *
 * The persisted extraction is refreshed only after success,
 * so a failed attempt does not replace a previous result.
 */
export function useProcessDocument(documentId: string) {
  const queryClient = useQueryClient();

  return useMutation<ProcessDocumentResponse, Error>({
    // The backend accepts a document ID and requires no request body.
    mutationFn: () => processDocument(documentId),

    // A successful attempt may have created a new extraction result.
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: PROCESSING_RESULT_QUERY_KEY(documentId),
        exact: true,
      });
    },

    // Always refresh the attempt history and document status.
    onSettled: async () => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: ["documents", documentId],
          exact: true,
        }),

        queryClient.invalidateQueries({
          queryKey: ["documents", documentId, "processing-history"],
          exact: true,
        }),

        queryClient.invalidateQueries({
          queryKey: DOCUMENTS_QUERY_KEY,
          exact: true,
        }),
      ]);
    },
  });
}
