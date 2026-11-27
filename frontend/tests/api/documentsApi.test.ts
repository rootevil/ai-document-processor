
import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from 'vitest'

import {
  uploadDocument,
  listDocuments,
  getDocument,
  downloadDocument,
  processDocument,
  getProcessingResult,
  getProcessingHistory,
} from '../../src/lib/api/documentsApi'

import { ApiError } from '../../src/lib/api/apiErrors'

const fetchMock = vi.fn<typeof fetch>()

const documentFixture = {
  id: 'document-123',
  original_filename: 'invoice.pdf',
  stored_filename: 'stored-invoice.pdf',
  content_type: 'application/pdf',
  file_size: 1024,
  status: 'uploaded',
  uploaded_at: '2026-11-27T10:00:00Z',
}

const processFixture = {
  document_id: 'document-123',
  attempt_id: 'attempt-123',
  attempt_number: 1,
  original_filename: 'invoice.pdf',
  status: 'completed',
  extraction: {
    document_type: 'invoice',
    fields: {},
  },
}

const attemptFixture = {
  attempt_id: 'attempt-123',
  document_id: 'document-123',
  attempt_number: 1,
  status: 'completed',
  error_code: null,
  error_message: null,
  started_at: '2026-11-27T10:00:00Z',
  completed_at: '2026-11-27T10:00:05Z',
}

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('Document API', () => {
  it('uploads a document and validates the response', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(documentFixture), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    const file = new File(
      ['invoice contents'],
      'invoice.pdf',
      { type: 'application/pdf' },
    )

    const result = await uploadDocument(file)

    expect(result).toEqual(documentFixture)
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/documents/upload'),
      expect.objectContaining({ method: 'POST' }),
    )
  })

  it('lists documents', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify([documentFixture]), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    const result = await listDocuments()

    expect(result).toEqual([documentFixture])
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/documents/'),
      expect.objectContaining({ method: 'GET' }),
    )
  })

  it('retrieves one document using its ID', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(documentFixture), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    const result = await getDocument('document-123')

    expect(result.id).toBe('document-123')
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/documents/document-123'),
      expect.objectContaining({ method: 'GET' }),
    )
  })

  it('downloads the original document', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response('original PDF contents', {
        status: 200,
        headers: { 'Content-Type': 'application/pdf' },
      }),
    )

    const result = await downloadDocument('document-123')

    expect(result).toBeInstanceOf(Blob)
    expect(await result.text()).toBe('original PDF contents')
  })

  it('starts processing without sending a request body', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(processFixture), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    const result = await processDocument('document-123')

    expect(result.attempt_id).toBe('attempt-123')
    expect(result.attempt_number).toBe(1)

    const options = fetchMock.mock.calls[0][1]

    expect(options?.method).toBe('POST')
    expect(options?.body).toBeUndefined()
  })

  it('retrieves a processing result', async () => {
    const resultFixture = {
      document_id: 'document-123',
      original_filename: 'invoice.pdf',
      status: 'completed',
      extraction: { document_type: 'invoice' },
      error_message: null,
      started_at: '2026-11-27T10:00:00Z',
      completed_at: '2026-11-27T10:00:05Z',
    }

    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(resultFixture), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    const result = await getProcessingResult('document-123')

    expect(result).toEqual(resultFixture)
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/documents/document-123/result'),
      expect.objectContaining({ method: 'GET' }),
    )
  })

  it('retrieves processing history', async () => {
    const historyFixture = {
      document_id: 'document-123',
      original_filename: 'invoice.pdf',
      total_attempts: 1,
      attempts: [attemptFixture],
    }

    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(historyFixture), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    const result = await getProcessingHistory('document-123')

    expect(result.total_attempts).toBe(1)
    expect(result.attempts[0].attempt_id).toBe('attempt-123')
  })

  it('rejects an invalid document response', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({ id: 'document-123' }),
        {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        },
      ),
    )

    await expect(
      getDocument('document-123'),
    ).rejects.toBeInstanceOf(ApiError)
  })
})
