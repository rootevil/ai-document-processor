import type { InvoiceFieldName, InvoiceScalar, ReviewStatus } from './invoice'

export type ReviewDecision =
  | 'approved'
  | 'corrected'
  | 'rejected'

export interface InvoiceFieldReviewRequest {
  field_name: InvoiceFieldName
  decision: ReviewDecision
  corrected_value?: string | number | null
}

export interface ReviewEvent {
  review_id: string
  attempt_id: string
  review_sequence: number
  field_name: InvoiceFieldName
  decision: ReviewDecision
  corrected_value: InvoiceScalar
  reviewer_id?: string | null
  reviewed_at: string
}

export interface OriginalAttemptExtractionResponse {
  attempt_id: string
  extracted_data: Record<string, unknown>
  created_at: string
}

export type ReviewSubmissionResponse = ReviewEvent

export interface ReviewHistoryResponse {
  document_id: string
  attempt_id: string
  total_reviews: number
  reviews: ReviewEvent[]
}

export interface LatestReviewsResponse {
  document_id: string
  attempt_id: string
  total_fields_reviewed: number
  reviews: Record<string, ReviewEvent>
}

export interface ReviewAwareField {
  original_value: unknown
  effective_value: unknown
  review_status: ReviewStatus
  latest_review: ReviewEvent | null
  [key: string]: unknown
}

export interface ReviewAwareExtractionResponse {
  document_id: string
  attempt_id: string
  created_at: string
  document_type: 'invoice' | 'unknown'
  fields: Record<string, ReviewAwareField>
}