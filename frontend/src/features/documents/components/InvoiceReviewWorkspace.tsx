import { useState } from "react";

import { useInvoiceFieldReviewHistory } from "../hooks/useInvoiceFieldReviewHistory";
import { useReviewAwareExtraction } from "../hooks/useReviewAwareExtraction";
import { useSubmitInvoiceFieldReview } from "../hooks/useSubmitInvoiceFieldReview";

import type { InvoiceFieldName, InvoiceScalar } from "../../../types/invoice";
import type { ReviewDecision, ReviewEvent } from "../../../types/review";

const FIELD_DEFINITIONS: ReadonlyArray<readonly [InvoiceFieldName, string]> = [
  ["invoice_number", "Invoice number"],
  ["invoice_date", "Invoice date"],
  ["due_date", "Due date"],
  ["vendor_name", "Vendor"],
  ["customer_name", "Customer"],
  ["subtotal", "Subtotal"],
  ["tax_amount", "Tax amount"],
  ["total_amount", "Total amount"],
  ["currency", "Currency"],
];

function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "Not detected";
  }

  return typeof value === "string" || typeof value === "number"
    ? String(value)
    : JSON.stringify(value) ?? String(value);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function statusClasses(status: string): string {
  switch (status) {
    case "approved":
      return "bg-green-100 text-green-800";
    case "corrected":
      return "bg-blue-100 text-blue-800";
    case "rejected":
      return "bg-red-100 text-red-800";
    default:
      return "bg-amber-100 text-amber-800";
  }
}

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(date);
}

function FieldEvidence({ field }: { field: Record<string, unknown> }) {
  const evidence = Array.isArray(field.evidence)
    ? field.evidence.filter(isRecord)
    : [];
  const references = Array.isArray(field.references)
    ? field.references.filter(isRecord)
    : [];

  if (evidence.length === 0 && references.length === 0) {
    return null;
  }

  return (
    <div className="mt-3 space-y-2 text-xs text-slate-600">
      {evidence.map((item, index) => {
        const reference = isRecord(item.reference) ? item.reference : null;
        const location = reference
          ? [
              typeof reference.page_number === "number"
                ? `Page ${reference.page_number}`
                : null,
              typeof reference.sheet_name === "string"
                ? reference.sheet_name
                : null,
              typeof reference.cell_reference === "string"
                ? reference.cell_reference
                : null,
            ]
              .filter(Boolean)
              .join(" · ")
          : "";

        return (
          <blockquote
            key={`${index}-${String(item.text ?? "evidence")}`}
            className="rounded-md border-l-2 border-slate-300 bg-white px-3 py-2"
          >
            {typeof item.text === "string" && (
              <p className="whitespace-pre-wrap">“{item.text}”</p>
            )}
            {location && <cite className="mt-1 block not-italic">{location}</cite>}
          </blockquote>
        );
      })}
      {references.length > 0 && evidence.length === 0 && (
        <p>
          References: {references
            .map((reference) => {
              if (typeof reference.page_number === "number") {
                return `Page ${reference.page_number}`;
              }
              if (typeof reference.cell_reference === "string") {
                return reference.cell_reference;
              }
              return null;
            })
            .filter(Boolean)
            .join(", ")}
        </p>
      )}
    </div>
  );
}

function ReviewField({
  fieldName,
  label,
  field,
  isPending,
  onSubmit,
}: {
  fieldName: InvoiceFieldName;
  label: string;
  field: Record<string, unknown>;
  isPending: boolean;
  onSubmit: (request: {
    field_name: InvoiceFieldName;
    decision: ReviewDecision;
    corrected_value?: InvoiceScalar;
  }) => Promise<boolean>;
}) {
  const [editing, setEditing] = useState(false);
  const [correctedValue, setCorrectedValue] = useState("");
  const status =
    typeof field.review_status === "string" ? field.review_status : "pending";
  const source = typeof field.source === "string" ? field.source : null;
  const normalizationStatus =
    typeof field.normalization_status === "string"
      ? field.normalization_status
      : null;

  async function submitCorrection(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const saved = await onSubmit({
      field_name: fieldName,
      decision: "corrected",
      corrected_value: correctedValue,
    });
    if (saved) {
      setEditing(false);
    }
  }

  return (
    <article className="rounded-lg border border-slate-200 bg-slate-50 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <h5 className="text-sm font-semibold text-slate-900">{label}</h5>
        <span
          className={`rounded-full px-2.5 py-1 text-xs font-semibold capitalize ${statusClasses(status)}`}
        >
          {status}
        </span>
      </div>

      <dl className="mt-3 grid gap-3 sm:grid-cols-2">
        <div>
          <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
            Original extracted value
          </dt>
          <dd className="mt-1 break-words text-sm text-slate-800">
            {displayValue(field.original_value)}
          </dd>
        </div>
        <div>
          <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
            Effective value
          </dt>
          <dd className="mt-1 break-words text-sm font-semibold text-slate-900">
            {displayValue(field.effective_value)}
          </dd>
        </div>
      </dl>

      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
        {source && <span>Source: {source}</span>}
        {normalizationStatus && (
          <span>Normalization: {normalizationStatus}</span>
        )}
      </div>
      <FieldEvidence field={field} />

      {editing ? (
        <form className="mt-4 flex flex-wrap items-end gap-2" onSubmit={submitCorrection}>
          <label className="min-w-48 flex-1 text-xs font-medium text-slate-700">
            Corrected value for {label}
            <input
              autoFocus
              value={correctedValue}
              onChange={(event) => setCorrectedValue(event.target.value)}
              className="mt-1 block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
            />
          </label>
          <button
            type="submit"
            disabled={isPending}
            className="rounded-md bg-blue-700 px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            Save correction
          </button>
          <button
            type="button"
            onClick={() => setEditing(false)}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700"
          >
            Cancel
          </button>
        </form>
      ) : (
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            disabled={isPending}
            onClick={() => void onSubmit({ field_name: fieldName, decision: "approved" })}
            className="rounded-md border border-green-300 bg-white px-3 py-1.5 text-xs font-medium text-green-800 disabled:opacity-50"
          >
            Approve {label}
          </button>
          <button
            type="button"
            disabled={isPending}
            onClick={() => {
              setCorrectedValue(
                field.effective_value === null || field.effective_value === undefined
                  ? ""
                  : String(field.effective_value),
              );
              setEditing(true);
            }}
            className="rounded-md border border-blue-300 bg-white px-3 py-1.5 text-xs font-medium text-blue-800 disabled:opacity-50"
          >
            Correct {label}
          </button>
          <button
            type="button"
            disabled={isPending}
            onClick={() => void onSubmit({ field_name: fieldName, decision: "rejected" })}
            className="rounded-md border border-red-300 bg-white px-3 py-1.5 text-xs font-medium text-red-800 disabled:opacity-50"
          >
            Reject {label}
          </button>
        </div>
      )}
    </article>
  );
}

export function InvoiceReviewWorkspace({
  documentId,
  attemptId,
  attemptNumber,
}: {
  documentId: string;
  attemptId: string;
  attemptNumber: number;
}) {
  const extractionQuery = useReviewAwareExtraction(documentId, attemptId);
  const historyQuery = useInvoiceFieldReviewHistory(documentId, attemptId);
  const reviewMutation = useSubmitInvoiceFieldReview(documentId, attemptId);

  async function submitReview(request: {
    field_name: InvoiceFieldName;
    decision: ReviewDecision;
    corrected_value?: InvoiceScalar;
  }): Promise<boolean> {
    try {
      await reviewMutation.mutateAsync(request);
      return true;
    } catch {
      // The mutation error is rendered above the field list.
      return false;
    }
  }

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div>
        <h3 className="font-semibold text-slate-900">Invoice field review</h3>
        <p className="mt-1 text-sm text-slate-500">
          Review attempt #{attemptNumber}. Decisions are saved as a history and
          do not overwrite the original extraction.
        </p>
      </div>

      {extractionQuery.isPending && (
        <p role="status" className="mt-4 text-sm text-slate-500">
          Loading review fields...
        </p>
      )}
      {extractionQuery.isError && (
        <div role="alert" className="mt-4 text-sm text-red-700">
          Unable to load review fields: {extractionQuery.error.message}
          <button
            type="button"
            onClick={() => void extractionQuery.refetch()}
            className="ml-2 font-medium underline"
          >
            Retry
          </button>
        </div>
      )}
      {reviewMutation.isError && (
        <p role="alert" className="mt-4 rounded-md bg-red-50 p-3 text-sm text-red-700">
          Unable to save review: {reviewMutation.error.message}
        </p>
      )}

      {extractionQuery.data && (
        <div className="mt-5 grid gap-4 lg:grid-cols-2">
          {FIELD_DEFINITIONS.map(([fieldName, label]) => {
            const field = extractionQuery.data.fields[fieldName];
            return (
              <ReviewField
                key={fieldName}
                fieldName={fieldName}
                label={label}
                field={field as Record<string, unknown>}
                isPending={reviewMutation.isPending}
                onSubmit={submitReview}
              />
            );
          })}
        </div>
      )}

      <div className="mt-8 border-t border-slate-200 pt-5">
        <h4 className="text-sm font-semibold text-slate-900">Review history</h4>
        {historyQuery.isPending && (
          <p role="status" className="mt-3 text-sm text-slate-500">
            Loading review history...
          </p>
        )}
        {historyQuery.isError && (
          <div role="alert" className="mt-3 text-sm text-red-700">
            Unable to load review history: {historyQuery.error.message}
            <button
              type="button"
              onClick={() => void historyQuery.refetch()}
              className="ml-2 font-medium underline"
            >
              Retry
            </button>
          </div>
        )}
        {historyQuery.data && historyQuery.data.reviews.length === 0 && (
          <p className="mt-3 text-sm text-slate-500">
            No field review decisions have been recorded for this attempt.
          </p>
        )}
        {historyQuery.data && historyQuery.data.reviews.length > 0 && (
          <ol className="mt-3 space-y-2">
            {[...historyQuery.data.reviews].reverse().map((review: ReviewEvent) => (
              <li
                key={review.review_id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-md bg-slate-50 px-3 py-2 text-sm"
              >
                <span>
                  <strong className="capitalize">{review.decision}</strong> · {review.field_name}
                  {review.decision === "corrected" && (
                    <> → {displayValue(review.corrected_value)}</>
                  )}
                </span>
                <time className="text-xs text-slate-500" dateTime={review.reviewed_at}>
                  {formatDate(review.reviewed_at)}
                </time>
              </li>
            ))}
          </ol>
        )}
      </div>
    </section>
  );
}
