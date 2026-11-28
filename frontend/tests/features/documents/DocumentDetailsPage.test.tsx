// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";

import { MemoryRouter, Route, Routes } from "react-router-dom";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { ApiError } from "../../../src/lib/api/apiErrors";
import {
  getDocument,
  processDocument,
  getProcessingResult,
  getProcessingHistory,
} from "../../../src/lib/api/documentsApi";

const mockedGetProcessingResult = vi.mocked(getProcessingResult);
const mockedGetProcessingHistory = vi.mocked(getProcessingHistory);

import { DocumentDetailsPage } from "../../../src/features/documents/pages/DocumentDetailsPage";

import type {
  DocumentRecord,
  ProcessDocumentResponse,
} from "../../../src/types/document";

// Mock API calls so the tests do not require a running backend.
vi.mock("../../../src/lib/api/documentsApi", () => ({
  getDocument: vi.fn(),
  processDocument: vi.fn(),
  getProcessingResult: vi.fn(),
  getProcessingHistory: vi.fn(),
}));

const mockedGetDocument = vi.mocked(getDocument);
const mockedProcessDocument = vi.mocked(processDocument);

const documentFixture: DocumentRecord = {
  id: "document-123",
  original_filename: "invoice.pdf",
  stored_filename: "stored-invoice.pdf",
  content_type: "application/pdf",
  file_size: 1024,
  status: "uploaded",
  uploaded_at: "2026-11-27T10:00:00Z",
};

// A realistic successful processing response.
// Keep the attempt metadata consistent with the assertions below.
const processingFixture: ProcessDocumentResponse = {
  document_id: "document-123",
  attempt_id: "attempt-123",
  attempt_number: 1,
  original_filename: "invoice.pdf",
  status: "completed",
  extraction: {
    source_filename: "stored-invoice.pdf",
    file_type: "pdf",
    invoice_extraction: {
      document_type: "invoice",
      fields: {
        invoice_number: {
          value: "INV-1001",
          normalization_status: "normalized",
          source: "rule_based",
          references: [{ type: "page", page_number: 1 }],
        },
        invoice_date: {
          value: null,
          normalization_status: "missing",
          source: "rule_based",
          references: [],
        },
        due_date: {
          value: null,
          normalization_status: "missing",
          source: "rule_based",
          references: [],
        },
        vendor_name: {
          value: "Example Vendor",
          normalization_status: "normalized",
          source: "rule_based",
          references: [{ type: "page", page_number: 1 }],
        },
        customer_name: {
          value: "Example Customer",
          normalization_status: "normalized",
          source: "rule_based",
          references: [{ type: "page", page_number: 1 }],
        },
        subtotal: {
          value: "$1000",
          normalization_status: "normalized",
          source: "rule_based",
          references: [{ type: "page", page_number: 1 }],
        },
        tax_amount: {
          value: null,
          normalization_status: "missing",
          source: "rule_based",
          references: [],
        },
        total_amount: {
          value: "$1150",
          normalization_status: "normalized",
          source: "rule_based",
          references: [{ type: "page", page_number: 1 }],
        },
        currency: {
          value: "$",
          normalization_status: "needs_review",
          source: "rule_based",
          references: [{ type: "page", page_number: 1 }],
        },
      },
    },
  },
};

// Match the complete paragraph text rather than depending on how
// React splits adjacent text and numeric children into DOM nodes.
function findAttemptNumber(attemptNumber: number) {
  const expectedText = `Attempt #${attemptNumber}`;

  return screen.findByText((_, element) => {
    return (
      element?.tagName === "P" &&
      element.textContent?.replace(/\s+/g, " ").trim() === expectedText
    );
  });
}

function renderDetailsPage() {
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
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/documents/document-123"]}>
        <Routes>
          <Route
            path="/documents/:documentId"
            element={<DocumentDetailsPage />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();

  // A newly uploaded document has no saved extraction yet.
  mockedGetProcessingResult.mockRejectedValue(
    new ApiError("No processing result found", 404),
  );

  // Its processing history is initially empty.
  mockedGetProcessingHistory.mockResolvedValue({
    document_id: "document-123",
    original_filename: "invoice.pdf",
    total_attempts: 0,
    attempts: [],
  });
});

afterEach(() => {
  cleanup();
});

describe("Document details page", () => {
  it("displays document metadata returned by the API", async () => {
    mockedGetDocument.mockResolvedValue(documentFixture);

    renderDetailsPage();

    expect(
      await screen.findByRole("heading", { name: "invoice.pdf" }),
    ).toBeInTheDocument();

    expect(screen.getByText("application/pdf")).toBeInTheDocument();
    expect(screen.getByText("1.0 KB")).toBeInTheDocument();
    expect(screen.getByText("stored-invoice.pdf")).toBeInTheDocument();
    expect(screen.getByText("uploaded")).toBeInTheDocument();

    expect(mockedGetDocument).toHaveBeenCalledWith(
      "document-123",
      expect.any(AbortSignal),
    );

  });

  it("displays an API error when the document cannot be loaded", async () => {
    mockedGetDocument.mockRejectedValue(new Error("Document not found"));

    renderDetailsPage();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Document not found",
    );

    expect(
      screen.getByRole("link", { name: "Back to documents" }),
    ).toHaveAttribute("href", "/");
  });

  it("processes a document and displays the extraction result", async () => {
    mockedGetDocument.mockResolvedValue(documentFixture);
    mockedProcessDocument.mockResolvedValue(processingFixture);

    renderDetailsPage();

    // Wait until the document has loaded before starting processing.
    await screen.findByRole("heading", { name: "invoice.pdf" });

    fireEvent.click(screen.getByRole("button", { name: "Process document" }));

    // Verify the backend was called with the correct document ID.
    await waitFor(() => {
      expect(mockedProcessDocument).toHaveBeenCalledWith("document-123");
    });

    // Verify that the processing attempt is displayed.
    expect(await findAttemptNumber(1)).toBeInTheDocument();

    // Verify the structured invoice fields are displayed.
    expect(screen.getByText("Invoice number")).toBeInTheDocument();
    expect(screen.getByText("Vendor")).toBeInTheDocument();
    expect(screen.getByText("Currency")).toBeInTheDocument();
    expect(screen.getAllByText("Not detected")).toHaveLength(3);

    // Internal processing diagnostics must not appear as invoice fields.
    expect(screen.queryByText("source filename")).not.toBeInTheDocument();
    expect(screen.queryByText("business fields")).not.toBeInTheDocument();

    expect(screen.getByText(/Attempt ID:\s*attempt-123/)).toBeInTheDocument();

    expect(screen.getByText("INV-1001")).toBeInTheDocument();
    expect(screen.getByText("$1150")).toBeInTheDocument();
    expect(screen.getByText("completed")).toBeInTheDocument();
  });

  it("displays processing history, including unsuccessful attempts", async () => {
    mockedGetDocument.mockResolvedValue(documentFixture);
    mockedGetProcessingHistory.mockResolvedValue({
      document_id: "document-123",
      original_filename: "invoice.pdf",
      total_attempts: 2,
      attempts: [
        {
          attempt_id: "attempt-002",
          document_id: "document-123",
          attempt_number: 2,
          status: "failed",
          error_code: "EXTRACTION_FAILED",
          error_message: "The document could not be extracted.",
          started_at: "2026-11-27T10:05:00Z",
          completed_at: "2026-11-27T10:05:03Z",
        },
        {
          attempt_id: "attempt-001",
          document_id: "document-123",
          attempt_number: 1,
          status: "completed",
          error_code: null,
          error_message: null,
          started_at: "2026-11-27T10:00:00Z",
          completed_at: "2026-11-27T10:00:04Z",
        },
      ],
    });

    renderDetailsPage();

    expect(
      await screen.findByRole("heading", { name: "invoice.pdf" }),
    ).toBeInTheDocument();

    expect(
      await screen.findByRole("heading", { name: "Processing history" }),
    ).toBeInTheDocument();

    expect(screen.getByText("Total attempts: 2")).toBeInTheDocument();
    expect(await findAttemptNumber(2)).toBeInTheDocument();
    expect(await findAttemptNumber(1)).toBeInTheDocument();
    expect(screen.getByText("failed")).toBeInTheDocument();
    expect(screen.getByText("completed")).toBeInTheDocument();
    expect(
      screen.getByText("The document could not be extracted."),
    ).toBeInTheDocument();
    expect(screen.getByText("attempt-002")).toBeInTheDocument();
    expect(screen.getByText("attempt-001")).toBeInTheDocument();

    expect(mockedGetProcessingHistory).toHaveBeenCalledWith(
      "document-123",
      expect.any(AbortSignal),
    );
  });

  it("shows an empty state when there are no processing attempts", async () => {
    mockedGetDocument.mockResolvedValue(documentFixture);

    renderDetailsPage();

    expect(
      await screen.findByRole("heading", { name: "Processing history" }),
    ).toBeInTheDocument();

    expect(
      screen.getByText("No processing attempts have been recorded."),
    ).toBeInTheDocument();
    expect(screen.getByText("Total attempts: 0")).toBeInTheDocument();
  });

  it("disables the process button while processing is underway", async () => {
    mockedGetDocument.mockResolvedValue(documentFixture);

    // Keep the API request pending so we can inspect the loading state.
    let resolveProcessing!: (value: ProcessDocumentResponse) => void;

    mockedProcessDocument.mockReturnValue(
      new Promise((resolve) => {
        resolveProcessing = resolve;
      }),
    );

    renderDetailsPage();

    await screen.findByRole("heading", { name: "invoice.pdf" });

    fireEvent.click(screen.getByRole("button", { name: "Process document" }));

    // The button should be disabled while the request is pending.

    // Wait for React to render the pending mutation state.
    const processingButton = await screen.findByRole("button", {
      name: "Processing...",
    });

    expect(processingButton).toBeDisabled();

    expect(screen.getByRole("status")).toHaveTextContent(
      "Document processing is underway.",
    );

    // Resolve the request so the test does not leave a pending mutation.
    resolveProcessing(processingFixture);

    expect(await findAttemptNumber(1)).toBeInTheDocument();
  });

  it("displays a processing error and allows the user to retry", async () => {
    mockedGetDocument.mockResolvedValue(documentFixture);

    mockedProcessDocument
      .mockRejectedValueOnce(new Error("Processing service unavailable"))
      .mockResolvedValueOnce({
        ...processingFixture,
        attempt_id: "attempt-124",
        attempt_number: 2,
      });

    renderDetailsPage();

    await screen.findByRole("heading", { name: "invoice.pdf" });

    // First attempt fails.
    fireEvent.click(screen.getByRole("button", { name: "Process document" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Processing service unavailable",
    );

    // The user can start another attempt after the failure.
    fireEvent.click(screen.getByRole("button", { name: "Process document" }));

    expect(await findAttemptNumber(2)).toBeInTheDocument();

    expect(mockedProcessDocument).toHaveBeenCalledTimes(2);
  });

  it("refreshes processing history after a failed attempt", async () => {
    mockedGetDocument.mockResolvedValue(documentFixture);
    mockedProcessDocument.mockRejectedValue(new Error("Extraction failed"));

    // The first history request is empty. After the failed attempt, the
    // invalidated query returns the newly recorded failed attempt.
    mockedGetProcessingHistory
      .mockResolvedValueOnce({
        document_id: "document-123",
        original_filename: "invoice.pdf",
        total_attempts: 0,
        attempts: [],
      })
      .mockResolvedValueOnce({
        document_id: "document-123",
        original_filename: "invoice.pdf",
        total_attempts: 1,
        attempts: [
          {
            attempt_id: "attempt-failed-001",
            document_id: "document-123",
            attempt_number: 1,
            status: "failed",
            error_code: "EXTRACTION_FAILED",
            error_message: "Extraction failed",
            started_at: "2026-11-28T10:00:00Z",
            completed_at: "2026-11-28T10:00:03Z",
          },
        ],
      });

    renderDetailsPage();

    await screen.findByRole("heading", { name: "invoice.pdf" });

    expect(
      await screen.findByText("No processing attempts have been recorded."),
    ).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", { name: "Process document" }),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Extraction failed",
    );

    // onSettled should invalidate and refetch processing history.
    await waitFor(() => {
      expect(mockedGetProcessingHistory).toHaveBeenCalledTimes(2);
    });

    expect(await findAttemptNumber(1)).toBeInTheDocument();
    expect(screen.getByText("failed")).toBeInTheDocument();
    expect(screen.getByText("attempt-failed-001")).toBeInTheDocument();
    expect(screen.getByText("Total attempts: 1")).toBeInTheDocument();
  });
});
