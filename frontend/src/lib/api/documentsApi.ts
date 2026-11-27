import {
  apiGet,
  apiGetBlob,
  apiPostEmpty,
  apiPostFile,
  validateApiResponse,
} from './apiClient'

import {
  documentRecordSchema,
  processDocumentResponseSchema,
  processingResultSchema,
  processingHistorySchema,
} from '../validation/documentSchemas'

import type {
  DocumentRecord,
  ProcessDocumentResponse,
  ProcessingResultResponse,
  ProcessingHistoryResponse,
} from '../../types/document'

/**
 * Upload a document to the backend.
 *
 * The backend expects multipart/form-data with the field name "file".
 */
export async function uploadDocument(
  file: File,
  signal?: AbortSignal,
): Promise<DocumentRecord> {
  const response = await apiPostFile<unknown>(
    'documents/upload',
    file,
    { signal },
  )

  return validateApiResponse(documentRecordSchema, response)
}

/**
 * Retrieve all uploaded documents.
 */
export async function listDocuments(
  signal?: AbortSignal,
): Promise<DocumentRecord[]> {
  const response = await apiGet<unknown[]>(
    'documents/',
    { signal },
  )

  return validateApiResponse(
    documentRecordSchema.array(),
    response,
  )
}

/**
 * Retrieve one document by its ID.
 */
export async function getDocument(
  documentId: string,
  signal?: AbortSignal,
): Promise<DocumentRecord> {
  const response = await apiGet<unknown>(
    `documents/${encodeURIComponent(documentId)}`,
    { signal },
  )

  return validateApiResponse(documentRecordSchema, response)
}

/**
 * Download the original uploaded document.
 */
export function downloadDocument(
  documentId: string,
  signal?: AbortSignal,
): Promise<Blob> {
  return apiGetBlob(
    `documents/${encodeURIComponent(documentId)}/download`,
    { signal },
  )
}

/**
 * Start document processing.
 *
 * The backend endpoint accepts no request body.
 */
export async function processDocument(
  documentId: string,
  signal?: AbortSignal,
): Promise<ProcessDocumentResponse> {
  const response = await apiPostEmpty<unknown>(
    `documents/${encodeURIComponent(documentId)}/process`,
    { signal },
  )

  return validateApiResponse(
    processDocumentResponseSchema,
    response,
  )
}

/**
 * Retrieve the saved extraction result for a document.
 */
export async function getProcessingResult(
  documentId: string,
  signal?: AbortSignal,
): Promise<ProcessingResultResponse> {
  const response = await apiGet<unknown>(
    `documents/${encodeURIComponent(documentId)}/result`,
    { signal },
  )

  return validateApiResponse(
    processingResultSchema,
    response,
  )
}

/**
 * Retrieve the processing attempt history for a document.
 */
export async function getProcessingHistory(
  documentId: string,
  signal?: AbortSignal,
): Promise<ProcessingHistoryResponse> {
  const response = await apiGet<unknown>(
    `documents/${encodeURIComponent(documentId)}/history`,
    { signal },
  )

  return validateApiResponse(
    processingHistorySchema,
    response,
  )
}