"""
Typed response contracts for the invoice review API.

These models define what the backend returns to frontend clients.
They do not change extraction, persistence, or review behaviour.
"""

from typing import Any, Literal

from pydantic import ConfigDict, StrictFloat, StrictInt, StrictStr

from app.schemas.invoice import InvoiceSchemaModel, ReviewStatus


# Supported invoice fields and human review decisions.
InvoiceReviewFieldName = Literal[
    "invoice_number",
    "invoice_date",
    "due_date",
    "vendor_name",
    "customer_name",
    "subtotal",
    "tax_amount",
    "total_amount",
    "currency",
]

InvoiceReviewDecision = Literal[
    "approved",
    "corrected",
    "rejected",
]

ReviewScalar = StrictStr | StrictInt | StrictFloat | None

class ReviewEventResponse(InvoiceSchemaModel):
    """One persisted human review event."""

    review_id: str
    attempt_id: str

    # Monotonically increasing sequence within the attempt.
    # This preserves the repository's review ordering information.
    review_sequence: int

    field_name: InvoiceReviewFieldName
    decision: InvoiceReviewDecision
    corrected_value: ReviewScalar = None
    reviewer_id: str | None = None
    reviewed_at: str

class OriginalAttemptExtractionResponse(InvoiceSchemaModel):
    """Immutable machine extraction snapshot for one attempt."""

    attempt_id: str
    extracted_data: dict[str, Any]
    created_at: str


class ReviewSubmissionResponse(ReviewEventResponse):
    """Response returned after submitting a review decision."""

    pass


class ReviewHistoryResponse(InvoiceSchemaModel):
    """Complete chronological review history for an attempt."""

    document_id: str
    attempt_id: str
    total_reviews: int
    reviews: list[ReviewEventResponse]


class LatestReviewsResponse(InvoiceSchemaModel):
    """Latest review decision independently for each reviewed field."""

    document_id: str
    attempt_id: str
    total_fields_reviewed: int
    reviews: dict[str, ReviewEventResponse]


class ReviewAwareFieldResponse(InvoiceSchemaModel):
    """
    Derived field representation.

    Original extraction metadata is retained as additional fields.
    This is important because the extraction contract may grow later.
    """

    model_config = ConfigDict(
        extra="allow",
        validate_assignment=True,
    )

    original_value: Any = None
    effective_value: Any = None
    review_status: ReviewStatus = ReviewStatus.PENDING
    latest_review: ReviewEventResponse | None = None


class ReviewAwareExtractionResponse(InvoiceSchemaModel):
    """Original invoice extraction combined with human review decisions."""

    document_id: str
    attempt_id: str
    created_at: str
    document_type: Literal["invoice", "unknown"]
    fields: dict[str, ReviewAwareFieldResponse]
