import { z } from 'zod'

export const invoiceFieldNameSchema = z.enum([
  'invoice_number',
  'invoice_date',
  'due_date',
  'vendor_name',
  'customer_name',
  'subtotal',
  'tax_amount',
  'total_amount',
  'currency',
])

export const invoiceScalarSchema = z.union([
  z.string(),
  z.number(),
  z.null(),
])

export const evidenceReferenceSchema = z.object({
  type: z.enum(['page', 'cell']),
  page_number: z.number().int().nullable().optional(),
  sheet_name: z.string().nullable().optional(),
  cell_reference: z.string().nullable().optional(),
  row_number: z.number().int().nullable().optional(),
  column_number: z.number().int().nullable().optional(),
})

export const evidenceSchema = z.object({
  text: z.string().min(1),
  reference: evidenceReferenceSchema.nullable(),
})

export const invoiceFieldSchema = z.object({
  value: invoiceScalarSchema,
  normalized_value: invoiceScalarSchema,
  normalization_status: z.string().nullable(),
  references: z.array(evidenceReferenceSchema),
  evidence: z.array(evidenceSchema),
  source: z.enum(['rule_based', 'ai', 'human']).nullable(),
  confidence: z.number().min(0).max(1).nullable(),
  validation_status: z.enum([
    'pending',
    'valid',
    'invalid',
    'needs_review',
  ]),
  review_status: z.enum([
    'pending',
    'approved',
    'corrected',
    'rejected',
  ]),
})

export const invoiceFieldsSchema = z.object({
  invoice_number: invoiceFieldSchema,
  invoice_date: invoiceFieldSchema,
  due_date: invoiceFieldSchema,
  vendor_name: invoiceFieldSchema,
  customer_name: invoiceFieldSchema,
  subtotal: invoiceFieldSchema,
  tax_amount: invoiceFieldSchema,
  total_amount: invoiceFieldSchema,
  currency: invoiceFieldSchema,
})

export const invoiceExtractionSchema = z.object({
  document_type: z.enum(['invoice', 'unknown']),
  fields: invoiceFieldsSchema,
})