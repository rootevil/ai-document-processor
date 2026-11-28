import { useQuery } from "@tanstack/react-query";

import { getReviewAwareExtraction } from "../../../lib/api/reviewApi";

export const REVIEW_AWARE_EXTRACTION_QUERY_KEY = (
  documentId: string,
  attemptId: string,
) => ["documents", documentId, "attempts", attemptId, "review-aware-extraction"] as const;

export function useReviewAwareExtraction(
  documentId: string,
  attemptId: string,
) {
  return useQuery({
    queryKey: REVIEW_AWARE_EXTRACTION_QUERY_KEY(documentId, attemptId),
    queryFn: ({ signal }) =>
      getReviewAwareExtraction(documentId, attemptId, signal),
    enabled: documentId.length > 0 && attemptId.length > 0,
    retry: false,
  });
}
