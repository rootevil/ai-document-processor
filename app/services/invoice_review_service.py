
"""
Review-aware invoice extraction service.

Combines the immutable machine extraction snapshot with the
latest human review decisions to produce an effective result.

This service is read-only. It never modifies the original
extraction or the review history.
"""

from copy import deepcopy

from app.services.processing_repository import (
    get_processing_attempt_result,
    get_latest_invoice_field_reviews,
)


SUPPORTED_INVOICE_FIELDS = (
    "invoice_number",
    "invoice_date",
    "due_date",
    "vendor_name",
    "customer_name",
    "subtotal",
    "tax_amount",
    "total_amount",
    "currency",
)


def get_review_aware_extraction(attempt_id: str) -> dict | None:
    """
    Build a review-aware extraction result for one processing attempt.

    Effective-value rules:
    - No review: retain the original extracted value.
    - Approved: retain the original extracted value.
    - Corrected: use the latest corrected value.
    - Rejected: expose no effective value.

    Original extraction data and review events remain unchanged.
    """

    # Retrieve the immutable extraction snapshot.
    snapshot = get_processing_attempt_result(attempt_id)

    if snapshot is None:
        return None

    # Retrieve the latest human decision independently for each field.
    latest_reviews = get_latest_invoice_field_reviews(attempt_id)

    # Work on a copy so the stored extraction is never modified.
    extraction_data = deepcopy(snapshot["extracted_data"])

    invoice_extraction = extraction_data.get("invoice_extraction", {})

    original_fields = invoice_extraction.get("fields", {})

    review_aware_fields = {}

    # Include all supported invoice fields, even when extraction
    # did not produce a value for a particular field.
    for field_name in SUPPORTED_INVOICE_FIELDS:
        original_field = deepcopy(
            original_fields.get(field_name, {})
        )

        original_value = original_field.get("value")

        review = latest_reviews.get(field_name)

        # No review means the machine prediction remains pending.
        if review is None:
            review_status = "pending"
            effective_value = original_value

        else:
            decision = review["decision"]
            review_status = decision

            if decision == "approved":
                effective_value = original_value

            elif decision == "corrected":
                effective_value = review["corrected_value"]

            elif decision == "rejected":
                effective_value = None

            else:
                # Defensive protection against unexpected stored data.
                raise ValueError(
                    f"Unsupported review decision: {decision}"
                )

        # Preserve the complete original field information and
        # add the derived review-aware values.
        review_aware_fields[field_name] = {
            **original_field,
            "original_value": original_value,
            "effective_value": effective_value,
            "review_status": review_status,
            "latest_review": deepcopy(review),
        }

    # Keep the document classification and attempt metadata.
    return {
        "attempt_id": snapshot["attempt_id"],
        "created_at": snapshot["created_at"],
        "document_type": invoice_extraction.get(
            "document_type",
            "unknown",
        ),
        "fields": review_aware_fields,
    }
