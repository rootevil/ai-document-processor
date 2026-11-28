// @vitest-environment jsdom

import '@testing-library/jest-dom/vitest'

import {
  describe,
  expect,
  it,
  vi,
} from 'vitest'

import {
  renderHook,
  waitFor,
} from '@testing-library/react'

import {
  QueryClient,
  QueryClientProvider,
} from '@tanstack/react-query'

import {
  getProcessingResult,
  getProcessingHistory,
} from '../../../src/lib/api/documentsApi'

import { ApiError } from '../../../src/lib/api/apiErrors'

import { useProcessingResult } from '../../../src/features/documents/hooks/useProcessingResult'
import { useProcessingHistory } from '../../../src/features/documents/hooks/useProcessingHistory'

import type {
  ProcessingResultResponse,
  ProcessingHistoryResponse,
} from '../../../src/types/document'

// Mock the HTTP layer; the hooks themselves remain real.
vi.mock('../../../src/lib/api/documentsApi', () => ({
  getProcessingResult: vi.fn(),
  getProcessingHistory: vi.fn(),
}))

const mockedGetProcessingResult = vi.mocked(getProcessingResult)
const mockedGetProcessingHistory = vi.mocked(getProcessingHistory)

const resultFixture: ProcessingResultResponse = {
  document_id: 'document-123',
  original_filename: 'invoice.pdf',
  status: 'completed',
  extraction: {
    invoice_extraction: {
      document_type: 'invoice',
      fields: {
        invoice_number: {
          value: 'INV-1001',
        },
      },
    },
  },
  error_message: null,
  started_at: '2026-11-27T10:00:00Z',
  completed_at: '2026-11-27T10:00:05Z',
}

const historyFixture: ProcessingHistoryResponse = {
  document_id: 'document-123',
  original_filename: 'invoice.pdf',
  total_attempts: 2,
  attempts: [
    {
      attempt_id: 'attempt-002',
      document_id: 'document-123',
      attempt_number: 2,
      status: 'completed',
      error_code: null,
      error_message: null,
      started_at: '2026-11-27T10:05:00Z',
      completed_at: '2026-11-27T10:05:05Z',
    },
    {
      attempt_id: 'attempt-001',
      document_id: 'document-123',
      attempt_number: 1,
      status: 'failed',
      error_code: 'PROCESSING_ERROR',
      error_message: 'Extraction failed',
      started_at: '2026-11-27T10:00:00Z',
      completed_at: '2026-11-27T10:00:01Z',
    },
  ],
}

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })

  return function Wrapper({
    children,
  }: {
    children: React.ReactNode
  }) {
    return (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    )
  }
}

describe('useProcessingResult', () => {
  it('loads the persisted extraction result', async () => {
    mockedGetProcessingResult.mockResolvedValue(resultFixture)

    const { result } = renderHook(
      () => useProcessingResult('document-123'),
      { wrapper: createWrapper() },
    )

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(result.current.data).toEqual(resultFixture)

    expect(mockedGetProcessingResult).toHaveBeenCalledWith(
      'document-123',
      expect.any(AbortSignal),
    )
  })

  it('returns null when no saved extraction exists', async () => {
    mockedGetProcessingResult.mockRejectedValue(
      new ApiError('No processing result found', 404),
    )

    const { result } = renderHook(
      () => useProcessingResult('document-123'),
      { wrapper: createWrapper() },
    )

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(result.current.data).toBeNull()
    expect(result.current.isError).toBe(false)
  })

  it('preserves unexpected API errors', async () => {
    mockedGetProcessingResult.mockRejectedValue(
      new ApiError('Internal server error', 500),
    )

    const { result } = renderHook(
      () => useProcessingResult('document-123'),
      { wrapper: createWrapper() },
    )

    await waitFor(() => {
      expect(result.current.isError).toBe(true)
    })

    expect(result.current.error).toBeInstanceOf(ApiError)
    expect(result.current.error?.message).toBe('Internal server error')
  })

  it('does not request a result without a document ID', async () => {
    const { result } = renderHook(
      () => useProcessingResult(''),
      { wrapper: createWrapper() },
    )

    expect(result.current.fetchStatus).toBe('idle')
    expect(mockedGetProcessingResult).not.toHaveBeenCalled()
  })
})

describe('useProcessingHistory', () => {
  it('loads all processing attempts, including failed attempts', async () => {
    mockedGetProcessingHistory.mockResolvedValue(historyFixture)

    const { result } = renderHook(
      () => useProcessingHistory('document-123'),
      { wrapper: createWrapper() },
    )

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(result.current.data?.total_attempts).toBe(2)
    expect(result.current.data?.attempts).toHaveLength(2)

    expect(
      result.current.data?.attempts.map((attempt) => attempt.status),
    ).toEqual(['completed', 'failed'])
  })

  it('does not request history without a document ID', () => {
    const { result } = renderHook(
      () => useProcessingHistory(''),
      { wrapper: createWrapper() },
    )

    expect(result.current.fetchStatus).toBe('idle')
    expect(mockedGetProcessingHistory).not.toHaveBeenCalled()
  })
})