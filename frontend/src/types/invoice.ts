export type InvoiceScalar =
  | string
  | number
  | null

export type InvoiceFieldName =
  | 'invoice_number'
  | 'invoice_date'
  | 'due_date'
  | 'vendor_name'
  | 'customer_name'
  | 'subtotal'
  | 'tax_amount'
  | 'total_amount'
  | 'currency'

export type ExtractionSource =
  | 'rule_based'
  | 'ai'
  | 'human'

export type ValidationStatus =
  | 'pending'
  | 'valid'
  | 'invalid'
  | 'needs_review'

export type ReviewStatus =
  | 'pending'
  | 'approved'
  | 'corrected'
  | 'rejected'

export interface EvidenceReference {
  type: 'page' | 'cell'
  page_number?: number | null
  sheet_name?: string | null
  cell_reference?: string | null
  row_number?: number | null
  column_number?: number | null
}

export interface Evidence {
  text: string
  reference: EvidenceReference | null
}

export interface InvoiceField {
  value: InvoiceScalar
  normalized_value: InvoiceScalar
  normalization_status: string | null
  references: EvidenceReference[]
  evidence: Evidence[]
  source: ExtractionSource | null
  confidence: number | null
  validation_status: ValidationStatus
  review_status: ReviewStatus
}

export interface InvoiceFields {
  invoice_number: InvoiceField
  invoice_date: InvoiceField
  due_date: InvoiceField
  vendor_name: InvoiceField
  customer_name: InvoiceField
  subtotal: InvoiceField
  tax_amount: InvoiceField
  total_amount: InvoiceField
  currency: InvoiceField
}

export interface InvoiceExtraction {
  document_type: 'invoice' | 'unknown'
  fields: InvoiceFields
}