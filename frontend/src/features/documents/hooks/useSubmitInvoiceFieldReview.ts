import { useMutation, useQueryClient } from "@tanstack/react-query";

import { submitInvoiceFieldReview } from "../../../lib/api/reviewApi";

import type { InvoiceFieldReviewRequest } from "../../../types/review";
import { INVOICE_FIELD_REVIEW_HISTORY_QUERY_KEY } from "./useInvoiceFieldReviewHistory";
import { REVIEW_AWARE_EXTRACTION_QUERY_KEY } from "./useReviewAwareExtraction";

export function useSubmitInvoiceFieldReview(
  documentId: string,
  attemptId: string,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (review: InvoiceFieldReviewRequest) =>
      submitInvoiceFieldReview(documentId, attemptId, review),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: REVIEW_AWARE_EXTRACTION_QUERY_KEY(documentId, attemptId),
          exact: true,
        }),
        queryClient.invalidateQueries({
          queryKey: INVOICE_FIELD_REVIEW_HISTORY_QUERY_KEY(documentId, attemptId),
          exact: true,
        }),
      ]);
    },
  });
}
