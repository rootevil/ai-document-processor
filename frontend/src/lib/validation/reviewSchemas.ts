import { z } from 'zod'
import {
  invoiceFieldNameSchema,
  invoiceScalarSchema,
} from './invoiceSchemas'

export const reviewDecisionSchema = z.enum([
  'approved',
  'corrected',
  'rejected',
])

export const invoiceFieldReviewRequestSchema = z.object({
  field_name: invoiceFieldNameSchema,
  decision: reviewDecisionSchema,
  corrected_value: z.union([
    z.string(),
    z.number(),
    z.null(),
  ]).optional(),
})

export const reviewEventSchema = z.object({
  review_id: z.string(),
  attempt_id: z.string(),
  review_sequence: z.number().int(),
  field_name: invoiceFieldNameSchema,
  decision: reviewDecisionSchema,
  corrected_value: invoiceScalarSchema,
  reviewer_id: z.string().nullable().optional(),
  reviewed_at: z.string(),
})

export const originalAttemptExtractionSchema = z.object({
  attempt_id: z.string(),
  extracted_data: z.record(z.string(), z.unknown()),
  created_at: z.string(),
})

export const reviewHistorySchema = z.object({
  document_id: z.string(),
  attempt_id: z.string(),
  total_reviews: z.number().int(),
  reviews: z.array(reviewEventSchema),
})

export const latestReviewsSchema = z.object({
  document_id: z.string(),
  attempt_id: z.string(),
  total_fields_reviewed: z.number().int(),
  reviews: z.record(z.string(), reviewEventSchema),
})

export const reviewAwareFieldSchema = z.object({
  original_value: z.unknown().optional(),
  effective_value: z.unknown().optional(),
  review_status: z.enum([
    'pending',
    'approved',
    'corrected',
    'rejected',
  ]),
  latest_review: reviewEventSchema.nullable(),
}).passthrough()

export const reviewAwareExtractionSchema = z.object({
  document_id: z.string(),
  attempt_id: z.string(),
  created_at: z.string(),
  document_type: z.enum(['invoice', 'unknown']),
  fields: z.record(z.string(), reviewAwareFieldSchema),
})