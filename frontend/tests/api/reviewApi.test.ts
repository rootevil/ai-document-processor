
import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from 'vitest'

import {
  getOriginalAttemptExtraction,
  submitInvoiceFieldReview,
  getInvoiceFieldReviewHistory,
  getLatestInvoiceFieldReviews,
  getReviewAwareExtraction,
} from '../../src/lib/api/reviewApi'

import { ApiError } from '../../src/lib/api/apiErrors'

const fetchMock = vi.fn<typeof fetch>()

const reviewFixture = {
  review_id: 'review-123',
  attempt_id: 'attempt-123',
  review_sequence: 1,
  field_name: 'invoice_number' as const,
  decision: 'corrected' as const,
  corrected_value: 'INV-2026-001',
  reviewer_id: null,
  reviewed_at: '2026-11-27T10:05:00Z',
}

const originalExtractionFixture = {
  attempt_id: 'attempt-123',
  extracted_data: {
    document_type: 'invoice',
    fields: {
      invoice_number: 'INV-OLD',
    },
  },
  created_at: '2026-11-27T10:00:00Z',
}

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('Review API', () => {
  it('retrieves the original attempt extraction', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(originalExtractionFixture), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    const result = await getOriginalAttemptExtraction(
      'document-123',
      'attempt-123',
    )

    expect(result).toEqual(originalExtractionFixture)

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining(
        '/documents/document-123/attempts/attempt-123/extraction',
      ),
      expect.objectContaining({ method: 'GET' }),
    )
  })

  it('submits a corrected invoice field review', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(reviewFixture), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    const result = await submitInvoiceFieldReview(
      'document-123',
      'attempt-123',
      {
        field_name: 'invoice_number',
        decision: 'corrected',
        corrected_value: 'INV-2026-001',
      },
    )

    expect(result).toEqual(reviewFixture)

    const [url, options] = fetchMock.mock.calls[0]

    expect(url).toContain(
      '/documents/document-123/attempts/attempt-123/reviews',
    )

    expect(options?.method).toBe('POST')

    expect(JSON.parse(options?.body as string)).toEqual({
      field_name: 'invoice_number',
      decision: 'corrected',
      corrected_value: 'INV-2026-001',
    })
  })


it('rejects an approved decision with a corrected value', async () => {
  await expect(
    submitInvoiceFieldReview(
      'document-123',
      'attempt-123',
      {
        field_name: 'invoice_number',
        decision: 'approved',
        corrected_value: 'INV-NEW',
      },
    ),
  ).rejects.toThrow()

  expect(fetchMock).not.toHaveBeenCalled()
})

it('accepts null as an explicit corrected value', async () => {
  const nullCorrectionFixture = {
    ...reviewFixture,
    corrected_value: null,
  }

  fetchMock.mockResolvedValueOnce(
    new Response(JSON.stringify(nullCorrectionFixture), {
      status: 201,
      headers: { 'Content-Type': 'application/json' },
    }),
  )

  const result = await submitInvoiceFieldReview(
    'document-123',
    'attempt-123',
    {
      field_name: 'invoice_number',
      decision: 'corrected',
      corrected_value: null,
    },
  )

  expect(result.corrected_value).toBeNull()
  expect(fetchMock).toHaveBeenCalledTimes(1)
})


  it('retrieves chronological review history', async () => {
    const historyFixture = {
      document_id: 'document-123',
      attempt_id: 'attempt-123',
      total_reviews: 1,
      reviews: [reviewFixture],
    }

    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(historyFixture), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    const result = await getInvoiceFieldReviewHistory(
      'document-123',
      'attempt-123',
    )

    expect(result.total_reviews).toBe(1)
    expect(result.reviews[0].review_id).toBe('review-123')
  })

  it('retrieves the latest review for each field', async () => {
    const latestFixture = {
      document_id: 'document-123',
      attempt_id: 'attempt-123',
      total_fields_reviewed: 1,
      reviews: {
        invoice_number: reviewFixture,
      },
    }

    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(latestFixture), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    const result = await getLatestInvoiceFieldReviews(
      'document-123',
      'attempt-123',
    )

    expect(result.total_fields_reviewed).toBe(1)
    expect(result.reviews.invoice_number.decision).toBe('corrected')
  })

  it('retrieves review-aware extraction', async () => {
    const awareFixture = {
      document_id: 'document-123',
      attempt_id: 'attempt-123',
      created_at: '2026-11-27T10:00:00Z',
      document_type: 'invoice',
      fields: {
        invoice_number: {
          original_value: 'INV-OLD',
          effective_value: 'INV-2026-001',
          review_status: 'corrected',
          latest_review: reviewFixture,
        },
      },
    }

    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(awareFixture), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    const result = await getReviewAwareExtraction(
      'document-123',
      'attempt-123',
    )

    expect(
      result.fields.invoice_number.original_value,
    ).toBe('INV-OLD')

    expect(
      result.fields.invoice_number.effective_value,
    ).toBe('INV-2026-001')

    expect(
      result.fields.invoice_number.review_status,
    ).toBe('corrected')
  })

  it('rejects an invalid review response', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          review_id: 'review-123',
          decision: 'unknown',
        }),
        {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        },
      ),
    )

    await expect(
      getInvoiceFieldReviewHistory(
        'document-123',
        'attempt-123',
      ),
    ).rejects.toBeInstanceOf(ApiError)
  })

  it('encodes document and attempt IDs in endpoint paths', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify(originalExtractionFixture), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    await getOriginalAttemptExtraction(
      'document/123',
      'attempt 123',
    )

    expect(fetchMock.mock.calls[0][0]).toContain(
      'documents/document%2F123/attempts/attempt%20123/extraction',
    )
  })
})
