export interface DocumentRecord {
  id: string
  original_filename: string
  stored_filename: string
  content_type: string
  file_size: number
  status: string
  uploaded_at: string
}

export interface ProcessingAttempt {
  attempt_id: string
  document_id: string
  attempt_number: number
  status: string
  error_code: string | null
  error_message: string | null
  started_at: string
  completed_at: string | null
}

export interface ProcessDocumentResponse {
  document_id: string
  attempt_id: string
  attempt_number: number
  original_filename: string
  status: string
  extraction: Record<string, unknown>
}

export interface ProcessingResultResponse {
  document_id: string
  original_filename: string
  status: string
  extraction: Record<string, unknown>
  error_message: string | null
  started_at: string
  completed_at: string | null
}

export interface ProcessingHistoryResponse {
  document_id: string
  original_filename: string
  total_attempts: number
  attempts: ProcessingAttempt[]
}