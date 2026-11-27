
import pytest

from app.db.database import initialize_database
from app.services.document_repository import create_document_record
from app.services.processing_repository import (
    start_processing_attempt,
    complete_processing_attempt,
    save_processing_attempt_result,
    record_invoice_field_review,
)
from app.services.invoice_review_service import (
    get_review_aware_extraction,
)


@pytest.fixture
def review_service_context(tmp_path, monkeypatch):
    """Create an isolated database and a completed extraction attempt."""

    monkeypatch.setattr(
        "app.db.database.settings.database_path",
        tmp_path / "document_ai.db",
    )

    initialize_database()

    document = create_document_record(
        original_filename="invoice.pdf",
        stored_filename="invoice.pdf",
        content_type="application/pdf",
        file_size=1024,
    )

    attempt = start_processing_attempt(document.id)

    extraction = {
        "invoice_extraction": {
            "document_type": "invoice",
            "fields": {
                "invoice_number": {
                    "value": "INV-1001",
                    "normalized_value": "INV-1001",
                    "source": "rule_based",
                    "review_status": "pending",
                },
                "vendor_name": {
                    "value": "Original Vendor",
                    "normalized_value": "Original Vendor",
                    "source": "ai",
                    "review_status": "pending",
                    "evidence": [{"text": "Original Vendor"}],
                },
                "total_amount": {
                    "value": 1200.00,
                    "normalized_value": 1200.00,
                    "source": "rule_based",
                    "review_status": "pending",
                },
            },
        }
    }

    save_processing_attempt_result(
        attempt_id=attempt["attempt_id"],
        extraction_data=extraction,
    )

    complete_processing_attempt(
        attempt_id=attempt["attempt_id"],
        status="completed",
    )

    return {
        "document": document,
        "attempt": attempt,
        "extraction": extraction,
    }


def test_unreviewed_field_uses_original_value(review_service_context):
    """An unreviewed field remains pending and retains its prediction."""

    attempt_id = review_service_context["attempt"]["attempt_id"]

    result = get_review_aware_extraction(attempt_id)

    field = result["fields"]["invoice_number"]

    assert field["original_value"] == "INV-1001"
    assert field["effective_value"] == "INV-1001"
    assert field["review_status"] == "pending"
    assert field["latest_review"] is None


def test_approved_field_uses_original_value(review_service_context):
    """Approval accepts the original machine extraction."""

    attempt_id = review_service_context["attempt"]["attempt_id"]

    record_invoice_field_review(
        attempt_id=attempt_id,
        field_name="invoice_number",
        decision="approved",
    )

    result = get_review_aware_extraction(attempt_id)

    field = result["fields"]["invoice_number"]

    assert field["original_value"] == "INV-1001"
    assert field["effective_value"] == "INV-1001"
    assert field["review_status"] == "approved"
    assert field["latest_review"]["decision"] == "approved"


def test_corrected_field_uses_corrected_value(review_service_context):
    """A correction becomes effective without replacing the original."""

    attempt_id = review_service_context["attempt"]["attempt_id"]

    record_invoice_field_review(
        attempt_id=attempt_id,
        field_name="vendor_name",
        decision="corrected",
        corrected_value="Correct Vendor",
    )

    result = get_review_aware_extraction(attempt_id)

    field = result["fields"]["vendor_name"]

    assert field["original_value"] == "Original Vendor"
    assert field["effective_value"] == "Correct Vendor"
    assert field["review_status"] == "corrected"

    # Original supporting evidence must remain available.
    assert field["evidence"] == [{"text": "Original Vendor"}]


def test_rejected_field_has_no_effective_value(review_service_context):
    """A rejected prediction must not be treated as accepted data."""

    attempt_id = review_service_context["attempt"]["attempt_id"]

    record_invoice_field_review(
        attempt_id=attempt_id,
        field_name="total_amount",
        decision="rejected",
    )

    result = get_review_aware_extraction(attempt_id)

    field = result["fields"]["total_amount"]

    assert field["original_value"] == 1200.00
    assert field["effective_value"] is None
    assert field["review_status"] == "rejected"


def test_latest_correction_replaces_earlier_approval(review_service_context):
    """The latest decision controls the effective value."""

    attempt_id = review_service_context["attempt"]["attempt_id"]

    record_invoice_field_review(
        attempt_id=attempt_id,
        field_name="invoice_number",
        decision="approved",
    )

    record_invoice_field_review(
        attempt_id=attempt_id,
        field_name="invoice_number",
        decision="corrected",
        corrected_value="INV-1002",
    )

    result = get_review_aware_extraction(attempt_id)

    field = result["fields"]["invoice_number"]

    assert field["original_value"] == "INV-1001"
    assert field["effective_value"] == "INV-1002"
    assert field["review_status"] == "corrected"


def test_latest_rejection_replaces_earlier_correction(review_service_context):
    """A later rejection removes the corrected value from effective data."""

    attempt_id = review_service_context["attempt"]["attempt_id"]

    record_invoice_field_review(
        attempt_id=attempt_id,
        field_name="total_amount",
        decision="corrected",
        corrected_value=1250.00,
    )

    record_invoice_field_review(
        attempt_id=attempt_id,
        field_name="total_amount",
        decision="rejected",
    )

    result = get_review_aware_extraction(attempt_id)

    field = result["fields"]["total_amount"]

    assert field["original_value"] == 1200.00
    assert field["effective_value"] is None
    assert field["review_status"] == "rejected"


def test_review_decisions_are_independent_per_field(review_service_context):
    """A decision for one field must not affect another field."""

    attempt_id = review_service_context["attempt"]["attempt_id"]

    record_invoice_field_review(
        attempt_id=attempt_id,
        field_name="invoice_number",
        decision="approved",
    )

    record_invoice_field_review(
        attempt_id=attempt_id,
        field_name="vendor_name",
        decision="corrected",
        corrected_value="Correct Vendor",
    )

    result = get_review_aware_extraction(attempt_id)

    assert result["fields"]["invoice_number"]["review_status"] == "approved"
    assert result["fields"]["vendor_name"]["review_status"] == "corrected"
    assert result["fields"]["total_amount"]["review_status"] == "pending"


def test_original_extraction_is_never_modified(review_service_context):
    """Generating the effective view must not alter the saved snapshot."""

    attempt_id = review_service_context["attempt"]["attempt_id"]
    original = review_service_context["extraction"]

    record_invoice_field_review(
        attempt_id=attempt_id,
        field_name="vendor_name",
        decision="corrected",
        corrected_value="Correct Vendor",
    )

    get_review_aware_extraction(attempt_id)

    from app.services.processing_repository import (
        get_processing_attempt_result,
    )

    saved = get_processing_attempt_result(attempt_id)

    assert saved["extracted_data"] == original


def test_missing_attempt_returns_none(review_service_context):
    """An unknown attempt must not produce an empty fabricated result."""

    result = get_review_aware_extraction("missing-attempt")

    assert result is None
