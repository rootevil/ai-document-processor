
import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from 'vitest'

import {
  apiGet,
  apiGetBlob,
  apiPost,
  apiPostEmpty,
  apiPostFile,
  validateApiResponse,
} from '../../src/lib/api/apiClient'

import { ApiError } from '../../src/lib/api/apiErrors'
import { z } from 'zod'

// Mock fetch so tests never depend on a running backend.
const fetchMock = vi.fn<typeof fetch>()

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('API client', () => {
  describe('GET requests', () => {
    it('sends a GET request and returns JSON data', async () => {
      const responseData = {
        id: 'document-123',
        status: 'uploaded',
      }

      fetchMock.mockResolvedValueOnce(
        new Response(JSON.stringify(responseData), {
          status: 200,
          headers: {
            'Content-Type': 'application/json',
          },
        }),
      )

      const result = await apiGet<typeof responseData>(
        'documents/document-123',
      )

      expect(result).toEqual(responseData)

      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/documents/document-123'),
        expect.objectContaining({
          method: 'GET',
          headers: expect.any(Headers),
        }),
      )

      const requestOptions = fetchMock.mock.calls[0][1]

      expect(
        new Headers(requestOptions?.headers).get('Accept'),
      ).toBe('application/json')
    })
  })

  describe('JSON POST requests', () => {
    it('sends a JSON request body', async () => {
      const requestBody = {
        field_name: 'invoice_number',
        decision: 'approved',
      }

      const responseData = {
        review_id: 'review-123',
        ...requestBody,
      }

      fetchMock.mockResolvedValueOnce(
        new Response(JSON.stringify(responseData), {
          status: 201,
          headers: {
            'Content-Type': 'application/json',
          },
        }),
      )

      const result = await apiPost<typeof responseData, typeof requestBody>(
        'documents/document-123/attempts/attempt-123/reviews',
        requestBody,
      )

      expect(result).toEqual(responseData)

      const requestOptions = fetchMock.mock.calls[0][1]

      expect(requestOptions?.method).toBe('POST')
      expect(requestOptions?.body).toBe(
        JSON.stringify(requestBody),
      )

      expect(
        new Headers(requestOptions?.headers).get('Content-Type'),
      ).toBe('application/json')
    })
  })

  describe('Empty POST requests', () => {
    it('sends POST without a body', async () => {
      fetchMock.mockResolvedValueOnce(
        new Response(
          JSON.stringify({ status: 'completed' }),
          {
            status: 200,
            headers: {
              'Content-Type': 'application/json',
            },
          },
        ),
      )

      const result = await apiPostEmpty<{ status: string }>(
        'documents/document-123/process',
      )

      expect(result).toEqual({
        status: 'completed',
      })

      const requestOptions = fetchMock.mock.calls[0][1]

      expect(requestOptions?.method).toBe('POST')
      expect(requestOptions?.body).toBeUndefined()

      expect(
        new Headers(requestOptions?.headers).has('Content-Type'),
      ).toBe(false)
    })
  })

  describe('File uploads', () => {
    it('sends a file using FormData without setting Content-Type manually', async () => {
      fetchMock.mockResolvedValueOnce(
        new Response(
          JSON.stringify({ id: 'document-123' }),
          {
            status: 201,
            headers: {
              'Content-Type': 'application/json',
            },
          },
        ),
      )

      const file = new File(
        ['invoice contents'],
        'invoice.pdf',
        { type: 'application/pdf' },
      )

      const result = await apiPostFile<{ id: string }>(
        'documents/upload',
        file,
      )

      expect(result.id).toBe('document-123')

      const requestOptions = fetchMock.mock.calls[0][1]

      expect(requestOptions?.method).toBe('POST')
      expect(requestOptions?.body).toBeInstanceOf(FormData)

      const formData = requestOptions?.body as FormData

      expect(formData.get('file')).toBe(file)

      expect(
        new Headers(requestOptions?.headers).has('Content-Type'),
      ).toBe(false)
    })
  })

  describe('HTTP errors', () => {
    it('converts a FastAPI string detail into ApiError', async () => {
      fetchMock.mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            detail: 'Document not found',
          }),
          {
            status: 404,
            headers: {
              'Content-Type': 'application/json',
            },
          },
        ),
      )

      await expect(
        apiGet('documents/missing-document'),
      ).rejects.toMatchObject({
        name: 'ApiError',
        message: 'Document not found',
        status: 404,
      })
    })

    it('converts validation error messages into ApiError', async () => {
      fetchMock.mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            detail: [
              { msg: 'Field name is required' },
              { msg: 'Decision is invalid' },
            ],
          }),
          {
            status: 422,
            headers: {
              'Content-Type': 'application/json',
            },
          },
        ),
      )

      await expect(
        apiGet('documents/document-123'),
      ).rejects.toMatchObject({
        name: 'ApiError',
        message: 'Field name is required; Decision is invalid',
        status: 422,
      })
    })
  })

  describe('Invalid responses', () => {
    it('handles invalid JSON returned by the server', async () => {
      fetchMock.mockResolvedValueOnce(
        new Response('This is not JSON', {
          status: 200,
        }),
      )

      await expect(
        apiGet('documents/document-123'),
      ).rejects.toMatchObject({
        name: 'ApiError',
        message: 'The server returned an invalid JSON response.',
        status: 200,
      })
    })

    it('rejects data that does not match the Zod schema', () => {
      const schema = z.object({
        id: z.string(),
        status: z.enum(['uploaded', 'completed']),
      })

      expect(() =>
        validateApiResponse(schema, {
          id: 123,
          status: 'unknown',
        }),
      ).toThrow(ApiError)
    })
  })

  describe('Network errors', () => {
    it('converts network failures into ApiError', async () => {
      fetchMock.mockRejectedValueOnce(
        new TypeError('Network unavailable'),
      )

      await expect(
        apiGet('documents/document-123'),
      ).rejects.toMatchObject({
        name: 'ApiError',
        message: 'Unable to connect to the server. Check your connection and try again.',
        status: null,
      })
    })
  })

  describe('Request cancellation', () => {
    it('preserves AbortError instead of converting it into ApiError', async () => {
      fetchMock.mockRejectedValueOnce(
        new DOMException(
          'Request aborted',
          'AbortError',
        ),
      )

      const controller = new AbortController()

      await expect(
        apiGet(
          'documents/document-123',
          { signal: controller.signal },
        ),
      ).rejects.toMatchObject({
        name: 'AbortError',
      })
    })
  })

  describe('Blob downloads', () => {
    it('returns the downloaded file as a Blob', async () => {
      const fileContents = 'original invoice contents'

      fetchMock.mockResolvedValueOnce(
        new Response(fileContents, {
          status: 200,
          headers: {
            'Content-Type': 'application/pdf',
          },
        }),
      )

      const result = await apiGetBlob(
        'documents/document-123/download',
      )

      expect(result).toBeInstanceOf(Blob)
      expect(result.type).toBe('application/pdf')
      expect(await result.text()).toBe(fileContents)

      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/download'),
        expect.objectContaining({
          method: 'GET',
        }),
      )
    })
  })
})
