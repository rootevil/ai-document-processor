import { useQuery } from "@tanstack/react-query";

import { getInvoiceFieldReviewHistory } from "../../../lib/api/reviewApi";

export const INVOICE_FIELD_REVIEW_HISTORY_QUERY_KEY = (
  documentId: string,
  attemptId: string,
) => ["documents", documentId, "attempts", attemptId, "reviews"] as const;

export function useInvoiceFieldReviewHistory(
  documentId: string,
  attemptId: string,
) {
  return useQuery({
    queryKey: INVOICE_FIELD_REVIEW_HISTORY_QUERY_KEY(documentId, attemptId),
    queryFn: ({ signal }) =>
      getInvoiceFieldReviewHistory(documentId, attemptId, signal),
    enabled: documentId.length > 0 && attemptId.length > 0,
    retry: false,
  });
}
