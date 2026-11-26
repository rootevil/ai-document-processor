"""
Shared invoice extraction schemas.

These models define the structure of extracted invoice data, its source
references, supporting evidence, and its review state.

Important:
- A reference identifies a location in the source document.
- Evidence contains the actual text supporting an extracted value.
- The original value is preserved separately from its normalized value.
- These models define the contract; they do not perform extraction.
"""

from datetime import date, datetime
from enum import Enum
from typing import Literal

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    StrictFloat,
    StrictInt,
    StrictStr,
    model_validator,
)


# Supported scalar types for an invoice field.
# Strict types prevent accidental conversions such as True becoming 1.
InvoiceValue = StrictStr | StrictInt | StrictFloat | datetime | date | None


class InvoiceSchemaModel(BaseModel):
    """Base configuration shared by all invoice schema models."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )


class ExtractionSource(str, Enum):
    """Identifies how an extracted field value was produced."""

    RULE_BASED = "rule_based"
    AI = "ai"
    HUMAN = "human"


class ValidationStatus(str, Enum):
    """Describes the result of automated validation."""

    PENDING = "pending"
    VALID = "valid"
    INVALID = "invalid"
    NEEDS_REVIEW = "needs_review"


class ReviewStatus(str, Enum):
    """Describes the human review state of a field."""

    PENDING = "pending"
    APPROVED = "approved"
    CORRECTED = "corrected"
    REJECTED = "rejected"


class EvidenceReference(InvoiceSchemaModel):
    """
    Identifies where information appears in the original document.

    Page references are used for PDF documents.
    Cell references are used for spreadsheet documents.
    """

    type: Literal["page", "cell"]

    # PDF location.
    page_number: int | None = Field(default=None, ge=1)

    # Spreadsheet location.
    # The existing Excel extractor calls this worksheet_name.
    # sheet_name remains accepted for compatibility with existing callers.
    sheet_name: str | None = Field(
        default=None,
        validation_alias=AliasChoices("worksheet_name", "sheet_name"),
    )
    cell_reference: str | None = None

    # Optional numeric coordinates from the Excel cell extractor.
    row_number: int | None = Field(default=None, ge=1)
    column_number: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_location(self):
        """Ensure the required location details exist for each reference type."""

        if self.type == "page" and self.page_number is None:
            raise ValueError("A page reference requires page_number.")

        if self.type == "cell" and not self.cell_reference:
            raise ValueError("A cell reference requires cell_reference.")

        return self


class Evidence(InvoiceSchemaModel):
    """
    Exact source text that supports an extracted field value.

    The location is optional because some extraction methods, especially
    AI-based extraction, may not yet be able to identify the exact location.
    Missing evidence must not be invented.
    """

    text: StrictStr = Field(min_length=1)
    reference: EvidenceReference | None = None


class InvoiceField(InvoiceSchemaModel):
    """
    Represents one extracted invoice field and its processing state.

    `value` stores the original extracted value.
    `normalized_value` stores the normalized representation.
    Neither value should overwrite the other.
    """

    value: InvoiceValue = None
    normalized_value: InvoiceValue = None

    # Kept flexible for compatibility with the existing normalizer's statuses.
    normalization_status: str | None = None

    # Source locations and exact supporting text are separate concepts.
    references: list[EvidenceReference] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)

    # Provenance and review information.
    source: ExtractionSource | None = None
    confidence: float | None = Field(default=None, strict=True, ge=0.0, le=1.0)
    validation_status: ValidationStatus = ValidationStatus.PENDING
    review_status: ReviewStatus = ReviewStatus.PENDING


class InvoiceFields(InvoiceSchemaModel):
    """
    The MVP invoice field collection.

    These are the nine business fields currently supported by the
    rule-based and AI extraction services.
    """

    invoice_number: InvoiceField = Field(default_factory=InvoiceField)
    invoice_date: InvoiceField = Field(default_factory=InvoiceField)
    due_date: InvoiceField = Field(default_factory=InvoiceField)
    vendor_name: InvoiceField = Field(default_factory=InvoiceField)
    customer_name: InvoiceField = Field(default_factory=InvoiceField)
    subtotal: InvoiceField = Field(default_factory=InvoiceField)
    tax_amount: InvoiceField = Field(default_factory=InvoiceField)
    total_amount: InvoiceField = Field(default_factory=InvoiceField)
    currency: InvoiceField = Field(default_factory=InvoiceField)


class InvoiceExtraction(InvoiceSchemaModel):
    """
    Structured invoice extraction result.

    This is the top-level contract for the MVP invoice extraction output.
    It can represent an invoice or a document classified as unknown.
    """

    document_type: Literal["invoice", "unknown"] = "unknown"
    fields: InvoiceFields = Field(default_factory=InvoiceFields)


# =============================================================
# INVOICE FIELD REVIEW API SCHEMAS
# =============================================================

class InvoiceFieldReviewRequest(InvoiceSchemaModel):
    """
    Request body for submitting one human invoice-field decision.

    A correction stores a replacement value separately.
    Approval and rejection cannot include replacement values.
    """

    field_name: Literal[
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

    decision: Literal["approved", "corrected", "rejected"]

    corrected_value: StrictStr | StrictInt | StrictFloat | None = None

    @model_validator(mode="after")
    def validate_review_decision(self):
        """Ensure the replacement value matches the review decision."""

        if self.decision == "corrected" and self.corrected_value is None:
            raise ValueError(
                "A corrected decision requires corrected_value."
            )

        if self.decision in {"approved", "rejected"}:
            if self.corrected_value is not None:
                raise ValueError(
                    "Approved and rejected decisions cannot include "
                    "corrected_value."
                )

        return self
