
import {
  apiGet,
  apiPost,
  validateApiResponse,
} from './apiClient'

import {
  originalAttemptExtractionSchema,
  reviewHistorySchema,
  latestReviewsSchema,
  reviewAwareExtractionSchema,
  reviewEventSchema,
  invoiceFieldReviewRequestSchema,
} from '../validation/reviewSchemas'

import type {
  InvoiceFieldReviewRequest,
  OriginalAttemptExtractionResponse,
  ReviewSubmissionResponse,
  ReviewHistoryResponse,
  LatestReviewsResponse,
  ReviewAwareExtractionResponse,
} from '../../types/review'

/**
 * Build the base URL for operations belonging to one
 * document processing attempt.
 *
 * A review must always be associated with the exact
 * processing attempt that produced the extraction.
 */
function buildAttemptUrl(
  documentId: string,
  attemptId: string,
): string {
  return (
    `documents/${encodeURIComponent(documentId)}` +
    `/attempts/${encodeURIComponent(attemptId)}`
  )
}

/**
 * Retrieve the original, immutable extraction snapshot
 * for a processing attempt.
 *
 * This is the machine-generated extraction before
 * human review decisions are applied.
 */
export async function getOriginalAttemptExtraction(
  documentId: string,
  attemptId: string,
  signal?: AbortSignal,
): Promise<OriginalAttemptExtractionResponse> {
  const response = await apiGet<unknown>(
    `${buildAttemptUrl(documentId, attemptId)}/extraction`,
    { signal },
  )

  return validateApiResponse(
    originalAttemptExtractionSchema,
    response,
  )
}

/**
 * Submit a human review decision for one invoice field.
 *
 * Supported decisions:
 * - approved: accept the extracted value.
 * - corrected: replace it with the supplied corrected value.
 * - rejected: reject the extracted value.
 *
 * The backend remains responsible for enforcing
 * the decision-specific validation rules.
 */
export async function submitInvoiceFieldReview(
  documentId: string,
  attemptId: string,
  review: InvoiceFieldReviewRequest,
  signal?: AbortSignal,
): Promise<ReviewSubmissionResponse> {
  const validatedRequest =
    invoiceFieldReviewRequestSchema.parse(review)

  const response = await apiPost<unknown, InvoiceFieldReviewRequest>(
    `${buildAttemptUrl(documentId, attemptId)}/reviews`,
    validatedRequest,
    { signal },
  )

  return validateApiResponse(
    reviewEventSchema,
    response,
  )
}

/**
 * Retrieve the complete chronological review history
 * for a processing attempt.
 *
 * Multiple reviews of the same field are preserved.
 */
export async function getInvoiceFieldReviewHistory(
  documentId: string,
  attemptId: string,
  signal?: AbortSignal,
): Promise<ReviewHistoryResponse> {
  const response = await apiGet<unknown>(
    `${buildAttemptUrl(documentId, attemptId)}/reviews`,
    { signal },
  )

  return validateApiResponse(
    reviewHistorySchema,
    response,
  )
}

/**
 * Retrieve the latest review decision for each
 * reviewed invoice field.
 *
 * This provides the current review state without
 * discarding the complete historical event log.
 */
export async function getLatestInvoiceFieldReviews(
  documentId: string,
  attemptId: string,
  signal?: AbortSignal,
): Promise<LatestReviewsResponse> {
  const response = await apiGet<unknown>(
    `${buildAttemptUrl(documentId, attemptId)}/reviews/latest`,
    { signal },
  )

  return validateApiResponse(
    latestReviewsSchema,
    response,
  )
}

/**
 * Retrieve the review-aware extraction.
 *
 * This combines the original extraction with the
 * latest human decisions to produce effective values.
 *
 * The original machine extraction remains unchanged.
 */
export async function getReviewAwareExtraction(
  documentId: string,
  attemptId: string,
  signal?: AbortSignal,
): Promise<ReviewAwareExtractionResponse> {
  const response = await apiGet<unknown>(
    `${buildAttemptUrl(documentId, attemptId)}/review-aware-extraction`,
    { signal },
  )

  return validateApiResponse(
    reviewAwareExtractionSchema,
    response,
  )
}
