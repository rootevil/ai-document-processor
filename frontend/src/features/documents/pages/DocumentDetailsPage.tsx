import { useProcessingResult } from "../hooks/useProcessingResult";
import { useProcessingHistory } from "../hooks/useProcessingHistory";
import { ArrowLeft, FileText, LoaderCircle, Play } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { useDocument } from "../hooks/useDocument";
import { useProcessDocument } from "../hooks/useProcessDocument";
import { InvoiceReviewWorkspace } from "../components/InvoiceReviewWorkspace";

// Keep formatting consistent with the document workspace.
function formatFileSize(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }

  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }

  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function formatDate(value: string): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function getStatusClasses(status: string): string {
  switch (status.toLowerCase()) {
    case "completed":
    case "processed":
      return "bg-green-100 text-green-700";

    case "processing":
      return "bg-blue-100 text-blue-700";

    case "failed":
    case "error":
      return "bg-red-100 text-red-700";

    case "uploaded":
      return "bg-slate-100 text-slate-700";

    default:
      return "bg-amber-100 text-amber-700";
  }
}

/**
 * Render only the structured invoice fields intended for the reviewer.
 *
 * The extraction response can contain diagnostic information and raw page
 * content. Those details are deliberately not rendered as invoice fields.
 */
function ExtractionResults({ extraction }: { extraction: unknown }) {
  if (
    typeof extraction !== "object" ||
    extraction === null ||
    Array.isArray(extraction)
  ) {
    return (
      <p className="text-sm text-slate-500">
        No structured invoice extraction was returned.
      </p>
    );
  }

  const extractionRecord = extraction as Record<string, unknown>;
  const invoiceExtraction = extractionRecord.invoice_extraction;

  if (
    typeof invoiceExtraction !== "object" ||
    invoiceExtraction === null ||
    Array.isArray(invoiceExtraction)
  ) {
    return (
      <p className="text-sm text-slate-500">
        The processing response does not contain structured invoice fields.
      </p>
    );
  }

  const invoiceRecord = invoiceExtraction as Record<string, unknown>;
  const rawFields = invoiceRecord.fields;

  if (
    typeof rawFields !== "object" ||
    rawFields === null ||
    Array.isArray(rawFields)
  ) {
    return (
      <p className="text-sm text-slate-500">No invoice fields were returned.</p>
    );
  }

  const fields = rawFields as Record<string, unknown>;

  // Keep the display order consistent with the application's invoice schema.
  const invoiceFieldDefinitions = [
    ["invoice_number", "Invoice number"],
    ["invoice_date", "Invoice date"],
    ["due_date", "Due date"],
    ["vendor_name", "Vendor"],
    ["customer_name", "Customer"],
    ["subtotal", "Subtotal"],
    ["tax_amount", "Tax amount"],
    ["total_amount", "Total amount"],
    ["currency", "Currency"],
  ] as const;

  return (
    <dl className="mt-4 grid gap-4 sm:grid-cols-2">
      {invoiceFieldDefinitions.map(([fieldName, label]) => {
        const rawField = fields[fieldName];

        const field =
          typeof rawField === "object" &&
          rawField !== null &&
          !Array.isArray(rawField)
            ? (rawField as Record<string, unknown>)
            : {};

        const value = field.value;

        const displayValue =
          value === null || value === undefined || value === ""
            ? "Not detected"
            : typeof value === "string" || typeof value === "number"
              ? String(value)
              : JSON.stringify(value);

        const normalizationStatus =
          typeof field.normalization_status === "string"
            ? field.normalization_status
            : null;

        const source = typeof field.source === "string" ? field.source : null;

        const references = Array.isArray(field.references)
          ? field.references
          : [];

        const pageNumbers = references
          .filter(
            (reference): reference is Record<string, unknown> =>
              typeof reference === "object" &&
              reference !== null &&
              !Array.isArray(reference),
          )
          .map((reference) => reference.page_number)
          .filter(
            (pageNumber): pageNumber is number =>
              typeof pageNumber === "number",
          );

        return (
          <div
            key={fieldName}
            className="rounded-lg border border-slate-200 bg-slate-50 p-4"
          >
            <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
              {label}
            </dt>

            <dd className="mt-2 break-words text-sm font-semibold text-slate-900">
              {displayValue}
            </dd>

            <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500">
              {normalizationStatus && (
                <span>Normalization: {normalizationStatus}</span>
              )}

              {source && <span>Source: {source}</span>}

              {pageNumbers.length > 0 && (
                <span>Page: {pageNumbers.join(", ")}</span>
              )}
            </div>
          </div>
        );
      })}
    </dl>
  );
}

export function DocumentDetailsPage() {
  const { documentId } = useParams<{ documentId: string }>();
  const activeDocumentId = documentId ?? "";

  const documentQuery = useDocument(activeDocumentId);
  const processingMutation = useProcessDocument(activeDocumentId);
  const processingResultQuery = useProcessingResult(activeDocumentId);
  const processingHistoryQuery = useProcessingHistory(activeDocumentId);

  if (!documentId) {
    return (
      <section className="rounded-xl border border-red-200 bg-red-50 p-6">
        <h2 className="font-semibold text-red-800">Invalid document</h2>
        <p className="mt-2 text-sm text-red-700">
          A document ID is required to display this page.
        </p>
      </section>
    );
  }

  if (documentQuery.isPending) {
    return (
      <div
        role="status"
        className="rounded-xl border border-slate-200 bg-white px-6 py-12 text-center text-sm text-slate-500"
      >
        Loading document details...
      </div>
    );
  }

  if (documentQuery.isError) {
    return (
      <section className="space-y-4">
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-sm font-medium text-slate-600 hover:text-slate-900"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Back to documents
        </Link>

        <div
          role="alert"
          className="rounded-xl border border-red-200 bg-red-50 p-6"
        >
          <h2 className="font-semibold text-red-800">
            Unable to load document.
          </h2>

          <p className="mt-2 text-sm text-red-700">
            {documentQuery.error.message}
          </p>

          <button
            type="button"
            onClick={() => void documentQuery.refetch()}
            className="mt-4 rounded-lg border border-red-300 bg-white px-3 py-2 text-sm font-medium text-red-700 hover:bg-red-100"
          >
            Try again
          </button>
        </div>
      </section>
    );
  }

  const document = documentQuery.data;

  // The persisted result is the source of truth when it exists.
  // The mutation response is a fallback while the persisted query refreshes.
  const persistedResult = processingResultQuery.data;
  const latestMutationResult = processingMutation.data;

  const extraction =
    persistedResult?.extraction ?? latestMutationResult?.extraction ?? null;

  const processingStatus =
    persistedResult?.status ?? latestMutationResult?.status ?? "unknown";

  const attempts = processingHistoryQuery.data?.attempts ?? [];

  // History is returned newest first. A failed latest attempt must not be
  // mistaken for the attempt that produced the last successful extraction.
  const latestSuccessfulAttempt = attempts.find((attempt) => {
    const status = attempt.status.toLowerCase();
    return status === "completed" || status === "processed";
  });

  const attemptNumber =
    latestMutationResult?.attempt_number ??
    latestSuccessfulAttempt?.attempt_number;

  const attemptId =
    latestMutationResult?.attempt_id ?? latestSuccessfulAttempt?.attempt_id;
  const reviewAttempt = latestSuccessfulAttempt;

  const hasProcessingAttempts = attempts.length > 0;

  return (
    <section className="space-y-8">
      {/* Navigation back to the document workspace. */}
      <Link
        to="/"
        className="inline-flex items-center gap-2 text-sm font-medium text-slate-600 hover:text-slate-900"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden="true" />
        Back to documents
      </Link>

      {/* Document heading. */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-slate-600">
            <FileText className="h-6 w-6" aria-hidden="true" />
          </div>

          <div>
            <h2 className="break-all text-2xl font-semibold tracking-tight text-slate-900">
              {document.original_filename}
            </h2>
            <p className="mt-1 text-sm text-slate-500">Document details</p>
          </div>
        </div>

        <span
          className={[
            "inline-flex rounded-full px-3 py-1.5 text-sm font-medium",
            getStatusClasses(document.status),
          ].join(" ")}
        >
          {document.status}
        </span>
      </div>

      {/* Document metadata. */}
      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="text-base font-semibold text-slate-900">
          Document information
        </h3>

        <dl className="mt-5 grid gap-6 sm:grid-cols-2">
          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Original filename
            </dt>
            <dd className="mt-1 break-all text-sm text-slate-900">
              {document.original_filename}
            </dd>
          </div>

          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Document ID
            </dt>
            <dd className="mt-1 break-all font-mono text-sm text-slate-700">
              {document.id}
            </dd>
          </div>

          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Content type
            </dt>
            <dd className="mt-1 text-sm text-slate-900">
              {document.content_type}
            </dd>
          </div>

          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
              File size
            </dt>
            <dd className="mt-1 text-sm text-slate-900">
              {formatFileSize(document.file_size)}
            </dd>
          </div>

          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Uploaded
            </dt>
            <dd className="mt-1 text-sm text-slate-900">
              {formatDate(document.uploaded_at)}
            </dd>
          </div>

          <div>
            <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Stored filename
            </dt>
            <dd className="mt-1 break-all font-mono text-sm text-slate-700">
              {document.stored_filename}
            </dd>
          </div>
        </dl>
      </section>

      {/* Processing controls and current extraction result. */}
      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h3 className="font-semibold text-slate-900">
              Processing activity
            </h3>
            <p className="mt-1 text-sm text-slate-500">
              Extract structured information from this document.
            </p>
          </div>

          <button
            type="button"
            disabled={processingMutation.isPending}
            onClick={() => processingMutation.mutate()}
            className="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {processingMutation.isPending ? (
              <>
                <LoaderCircle
                  className="h-4 w-4 animate-spin"
                  aria-hidden="true"
                />
                Processing...
              </>
            ) : (
              <>
                <Play className="h-4 w-4" aria-hidden="true" />
                {hasProcessingAttempts || processingMutation.isSuccess
                  ? "Process again"
                  : "Process document"}
              </>
            )}
          </button>
        </div>

        {/* Show progress while the backend processes the document. */}
        {processingMutation.isPending && (
          <div
            role="status"
            className="mt-6 rounded-lg border border-blue-200 bg-blue-50 p-4"
          >
            <p className="text-sm font-medium text-blue-800">
              Document processing is underway.
            </p>
            <p className="mt-1 text-sm text-blue-700">
              Please wait while the system extracts document information.
            </p>
          </div>
        )}

        {/* Show API or processing errors and allow another attempt. */}
        {processingMutation.isError && (
          <div
            role="alert"
            className="mt-6 rounded-lg border border-red-200 bg-red-50 p-4"
          >
            <h4 className="text-sm font-semibold text-red-800">
              Processing failed
            </h4>
            <p className="mt-1 text-sm text-red-700">
              {processingMutation.error.message}
            </p>
            <p className="mt-2 text-xs text-red-600">
              You can retry processing using the button above.
            </p>
          </div>
        )}

        {/* A saved result is available even after the user leaves and reopens the page. */}
        {processingResultQuery.isPending && !latestMutationResult && (
          <p role="status" className="mt-6 text-sm text-slate-500">
            Checking for a saved extraction result...
          </p>
        )}

        {processingResultQuery.isError && (
          <div
            role="alert"
            className="mt-6 rounded-lg border border-red-200 bg-red-50 p-4"
          >
            <p className="text-sm text-red-700">
              Unable to load the saved extraction:{" "}
              {processingResultQuery.error.message}
            </p>
            <button
              type="button"
              onClick={() => void processingResultQuery.refetch()}
              className="mt-2 text-sm font-medium text-red-700 underline"
            >
              Try again
            </button>
          </div>
        )}

        {extraction && (
          <div className="mt-6 space-y-5">
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-green-200 bg-green-50 p-4">
              <div>
                <p className="text-sm font-semibold text-green-800">
                  Saved processing result
                </p>
                {attemptNumber !== undefined && (
                  <p className="mt-1 text-sm text-green-700">
                    Attempt #{attemptNumber}
                  </p>
                )}
              </div>

              <span
                className={[
                  "rounded-full px-3 py-1 text-xs font-semibold",
                  getStatusClasses(processingStatus),
                ].join(" ")}
              >
                {processingStatus}
              </span>
            </div>

            <div>
              <h4 className="text-sm font-semibold text-slate-900">
                Extraction results
              </h4>
              <ExtractionResults extraction={extraction} />
            </div>

            {attemptId && (
              <p className="break-all text-xs text-slate-500">
                Attempt ID: {attemptId}
              </p>
            )}
          </div>
        )}

        {!processingResultQuery.isPending &&
          !processingResultQuery.isError &&
          !extraction &&
          hasProcessingAttempts && (
            <p className="mt-6 rounded-lg bg-slate-50 p-4 text-sm text-slate-500">
              Processing attempts are recorded, but there is no successful
              extraction result available.
            </p>
          )}

        {!processingResultQuery.isPending &&
          !processingResultQuery.isError &&
          !extraction &&
          !hasProcessingAttempts &&
          !processingMutation.isPending &&
          !processingMutation.isError && (
            <p className="mt-6 rounded-lg bg-slate-50 p-4 text-sm text-slate-500">
              This document has not been processed yet. Select Process document
              to start an extraction attempt.
            </p>
          )}
      </section>

      {reviewAttempt && (
        <InvoiceReviewWorkspace
          documentId={activeDocumentId}
          attemptId={reviewAttempt.attempt_id}
          attemptNumber={reviewAttempt.attempt_number}
        />
      )}

      {/* Processing history includes both successful and failed attempts. */}
      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div>
          <h3 className="font-semibold text-slate-900">Processing history</h3>
          <p className="mt-1 text-sm text-slate-500">
            All recorded processing attempts, including unsuccessful ones.
          </p>
        </div>

        {processingHistoryQuery.isPending && (
          <p role="status" className="mt-4 text-sm text-slate-500">
            Loading processing history...
          </p>
        )}

        {processingHistoryQuery.isError && (
          <div role="alert" className="mt-4 text-sm text-red-700">
            Unable to load processing history:{" "}
            {processingHistoryQuery.error.message}
            <button
              type="button"
              onClick={() => void processingHistoryQuery.refetch()}
              className="ml-2 font-medium underline"
            >
              Retry
            </button>
          </div>
        )}

        {processingHistoryQuery.data && (
          <div className="mt-5 space-y-3">
            <p className="text-sm text-slate-500">
              Total attempts: {processingHistoryQuery.data.total_attempts}
            </p>

            {processingHistoryQuery.data.attempts.length === 0 ? (
              <p className="rounded-lg bg-slate-50 p-4 text-sm text-slate-500">
                No processing attempts have been recorded.
              </p>
            ) : (
              processingHistoryQuery.data.attempts.map((attempt) => (
                <div
                  key={attempt.attempt_id}
                  className="rounded-lg border border-slate-200 p-4"
                >
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <p className="text-sm font-semibold text-slate-900">
                      Attempt #{attempt.attempt_number}
                    </p>

                    <span
                      className={[
                        "rounded-full px-3 py-1 text-xs font-semibold",
                        getStatusClasses(attempt.status),
                      ].join(" ")}
                    >
                      {attempt.status}
                    </span>
                  </div>

                  <p className="mt-2 text-xs text-slate-500">
                    Started: {formatDate(attempt.started_at)}
                  </p>

                  {attempt.completed_at && (
                    <p className="mt-1 text-xs text-slate-500">
                      Completed: {formatDate(attempt.completed_at)}
                    </p>
                  )}

                  {attempt.error_code && (
                    <p className="mt-2 text-xs font-medium text-red-700">
                      Error code: {attempt.error_code}
                    </p>
                  )}

                  {attempt.error_message && (
                    <p className="mt-2 text-sm text-red-700">
                      {attempt.error_message}
                    </p>
                  )}

                  <p className="mt-2 break-all font-mono text-xs text-slate-400">
                    {attempt.attempt_id}
                  </p>
                </div>
              ))
            )}
          </div>
        )}
      </section>
    </section>
  );
}
