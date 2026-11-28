// @vitest-environment jsdom

import "@testing-library/jest-dom/vitest";

import { act, renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";

import {
  getInvoiceFieldReviewHistory,
  getReviewAwareExtraction,
  submitInvoiceFieldReview,
} from "../../../src/lib/api/reviewApi";
import { useInvoiceFieldReviewHistory } from "../../../src/features/documents/hooks/useInvoiceFieldReviewHistory";
import { useReviewAwareExtraction } from "../../../src/features/documents/hooks/useReviewAwareExtraction";
import { useSubmitInvoiceFieldReview } from "../../../src/features/documents/hooks/useSubmitInvoiceFieldReview";

vi.mock("../../../src/lib/api/reviewApi", () => ({
  getInvoiceFieldReviewHistory: vi.fn(),
  getReviewAwareExtraction: vi.fn(),
  submitInvoiceFieldReview: vi.fn(),
}));

const mockedGetInvoiceFieldReviewHistory = vi.mocked(
  getInvoiceFieldReviewHistory,
);
const mockedGetReviewAwareExtraction = vi.mocked(getReviewAwareExtraction);
const mockedSubmitInvoiceFieldReview = vi.mocked(submitInvoiceFieldReview);

const reviewAwareFixture = {
  document_id: "document-123",
  attempt_id: "attempt-123",
  created_at: "2026-11-27T10:00:00Z",
  document_type: "invoice" as const,
  fields: {
    invoice_number: {
      original_value: "INV-OLD",
      effective_value: "INV-OLD",
      review_status: "pending" as const,
      latest_review: null,
    },
  },
};

const historyFixture = {
  document_id: "document-123",
  attempt_id: "attempt-123",
  total_reviews: 0,
  reviews: [],
};

const reviewEventFixture = {
  review_id: "review-123",
  attempt_id: "attempt-123",
  review_sequence: 1,
  field_name: "invoice_number" as const,
  decision: "approved" as const,
  corrected_value: null,
  reviewer_id: null,
  reviewed_at: "2026-11-27T10:05:00Z",
};

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

describe("invoice review hooks", () => {
  it("loads attempt-scoped review data and refreshes it after a decision", async () => {
    mockedGetReviewAwareExtraction.mockResolvedValue(reviewAwareFixture);
    mockedGetInvoiceFieldReviewHistory.mockResolvedValue(historyFixture);
    mockedSubmitInvoiceFieldReview.mockResolvedValue(reviewEventFixture);

    const { result } = renderHook(
      () => ({
        extraction: useReviewAwareExtraction("document-123", "attempt-123"),
        history: useInvoiceFieldReviewHistory("document-123", "attempt-123"),
        submit: useSubmitInvoiceFieldReview("document-123", "attempt-123"),
      }),
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(result.current.extraction.isSuccess).toBe(true);
      expect(result.current.history.isSuccess).toBe(true);
    });

    expect(result.current.extraction.data?.fields.invoice_number.original_value)
      .toBe("INV-OLD");
    expect(mockedGetReviewAwareExtraction).toHaveBeenCalledWith(
      "document-123",
      "attempt-123",
      expect.any(AbortSignal),
    );

    await act(async () => {
      await result.current.submit.mutateAsync({
        field_name: "invoice_number",
        decision: "approved",
      });
    });

    expect(mockedSubmitInvoiceFieldReview).toHaveBeenCalledWith(
      "document-123",
      "attempt-123",
      { field_name: "invoice_number", decision: "approved" },
    );
    await waitFor(() => {
      expect(mockedGetReviewAwareExtraction).toHaveBeenCalledTimes(2);
      expect(mockedGetInvoiceFieldReviewHistory).toHaveBeenCalledTimes(2);
    });
  });

  it("does not request review data without an attempt ID", () => {
    const { result } = renderHook(
      () => ({
        extraction: useReviewAwareExtraction("document-123", ""),
        history: useInvoiceFieldReviewHistory("document-123", ""),
      }),
      { wrapper: createWrapper() },
    );

    expect(result.current.extraction.fetchStatus).toBe("idle");
    expect(result.current.history.fetchStatus).toBe("idle");
    expect(mockedGetReviewAwareExtraction).not.toHaveBeenCalled();
    expect(mockedGetInvoiceFieldReviewHistory).not.toHaveBeenCalled();
  });
});
