import { z } from 'zod'

export const documentRecordSchema = z.object({
  id: z.string(),
  original_filename: z.string(),
  stored_filename: z.string(),
  content_type: z.string(),
  file_size: z.number().int(),
  status: z.string(),
  uploaded_at: z.string().datetime(),
})

export const processingAttemptSchema = z.object({
  attempt_id: z.string(),
  document_id: z.string(),
  attempt_number: z.number().int(),
  status: z.string(),
  error_code: z.string().nullable(),
  error_message: z.string().nullable(),
  started_at: z.string(),
  completed_at: z.string().nullable(),
})

export const processDocumentResponseSchema = z.object({
  document_id: z.string(),
  attempt_id: z.string(),
  attempt_number: z.number().int(),
  original_filename: z.string(),
  status: z.string(),
  extraction: z.record(z.string(), z.unknown()),
})

export const processingResultSchema = z.object({
  document_id: z.string(),
  original_filename: z.string(),
  status: z.string(),
  extraction: z.record(z.string(), z.unknown()),
  error_message: z.string().nullable(),
  started_at: z.string(),
  completed_at: z.string().nullable(),
})

export const processingHistorySchema = z.object({
  document_id: z.string(),
  original_filename: z.string(),
  total_attempts: z.number().int(),
  attempts: z.array(processingAttemptSchema),
})