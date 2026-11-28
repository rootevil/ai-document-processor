// @vitest-environment jsdom
import '@testing-library/jest-dom/vitest'
import { MemoryRouter } from 'react-router-dom'
import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from 'vitest'

import {
  cleanup,
  render,
  screen,
  waitFor,
} from '@testing-library/react'

import userEvent from '@testing-library/user-event'

import {
  QueryClient,
  QueryClientProvider,
} from '@tanstack/react-query'

import {
  listDocuments,
  uploadDocument,
} from '../../../src/lib/api/documentsApi'

import { DocumentsPage } from '../../../src/features/documents/pages/DocumentsPage'
import { validateUploadFile } from '../../../src/lib/validation/uploadFile'

import type { DocumentRecord } from '../../../src/types/document'

// Mock the API boundary so these tests exercise the UI
// without depending on a running FastAPI server.
vi.mock('../../../src/lib/api/documentsApi', () => ({
  listDocuments: vi.fn(),
  uploadDocument: vi.fn(),
}))

const mockedListDocuments = vi.mocked(listDocuments)
const mockedUploadDocument = vi.mocked(uploadDocument)

const documentFixture: DocumentRecord = {
  id: 'document-123',
  original_filename: 'invoice.pdf',
  stored_filename: 'stored-invoice.pdf',
  content_type: 'application/pdf',
  file_size: 1024,
  status: 'uploaded',
  uploaded_at: '2026-11-27T10:00:00Z',
}

function renderDocumentsPage() {
  // A fresh query client prevents cached data leaking between tests.
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
  })

  // MemoryRouter provides the router context required by React Router Links.
  return render(
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>
        <DocumentsPage />
      </QueryClientProvider>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
})

afterEach(() => {
  cleanup()
})

describe('Documents workspace', () => {
  it('displays uploaded documents returned by the API', async () => {
    mockedListDocuments.mockResolvedValueOnce([
      documentFixture,
    ])

    renderDocumentsPage()

    expect(
      await screen.findByRole('link', { name: 'invoice.pdf' }),
    ).toBeInTheDocument()

    expect(
      screen.getByRole('link', { name: 'invoice.pdf' }),
    ).toHaveAttribute('href', '/documents/document-123')

    expect(screen.getByText('1.0 KB')).toBeInTheDocument()
    expect(screen.getByText('uploaded')).toBeInTheDocument()
  })

  it('shows an empty state when there are no documents', async () => {
    mockedListDocuments.mockResolvedValueOnce([])

    renderDocumentsPage()

    expect(
      await screen.findByText('No documents uploaded yet'),
    ).toBeInTheDocument()
  })

  it('uploads a supported file and refreshes the document list', async () => {
    mockedListDocuments
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([documentFixture])

    mockedUploadDocument.mockResolvedValueOnce(
      documentFixture,
    )

    const user = userEvent.setup()

    renderDocumentsPage()

    await screen.findByText('No documents uploaded yet')

    const file = new File(
      ['invoice contents'],
      'invoice.pdf',
      { type: 'application/pdf' },
    )

    const input = screen.getByLabelText('Choose a document')

    await user.upload(input, file)

    await waitFor(() => {
      expect(mockedUploadDocument).toHaveBeenCalledWith(file)
    })

    expect(
      await screen.findByText('Document uploaded successfully.'),
    ).toBeInTheDocument()

    expect(
      await screen.findByRole('link', { name: 'invoice.pdf' }),
    ).toBeInTheDocument()

    expect(mockedListDocuments).toHaveBeenCalledTimes(2)
  })

  it('rejects unsupported file extensions before uploading', async () => {
    mockedListDocuments.mockResolvedValueOnce([])

    const user = userEvent.setup({
      applyAccept: false,
    })

    renderDocumentsPage()

    await screen.findByText('No documents uploaded yet')

    const file = new File(
      ['unsupported contents'],
      'invoice.docx',
      { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' },
    )

    await user.upload(
      screen.getByLabelText('Choose a document'),
      file,
    )

    expect(
      await screen.findByRole('alert'),
    ).toHaveTextContent('Unsupported file type')

    expect(mockedUploadDocument).not.toHaveBeenCalled()
  })

  it('rejects files larger than 10 MB', () => {
    const oversizedFile = new File(
      [new Uint8Array(10 * 1024 * 1024 + 1)],
      'large-invoice.pdf',
      { type: 'application/pdf' },
    )

    expect(validateUploadFile(oversizedFile)).toContain(
      'maximum allowed size of 10 MB',
    )
  })

  it('displays API errors when document upload fails', async () => {
    mockedListDocuments.mockResolvedValueOnce([])

    mockedUploadDocument.mockRejectedValueOnce(
      new Error('Upload failed because the server rejected the file.'),
    )

    const user = userEvent.setup()

    renderDocumentsPage()

    await screen.findByText('No documents uploaded yet')

    const file = new File(
      ['invoice contents'],
      'invoice.pdf',
      { type: 'application/pdf' },
    )

    await user.upload(
      screen.getByLabelText('Choose a document'),
      file,
    )

    expect(
      await screen.findByRole('alert'),
    ).toHaveTextContent(
      'Upload failed because the server rejected the file.',
    )
  })
})
