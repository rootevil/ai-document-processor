"""
Tests for immutable invoice extraction snapshots and field-level reviews.

These tests define the expected repository behaviour before implementation.
"""

import sqlite3

import pytest

from app.db.database import initialize_database
from app.services.document_repository import create_document_record
from app.services import processing_repository

from app.services.processing_repository import (
    start_processing_attempt,
    complete_processing_attempt,
)


SUPPORTED_FIELDS = {
    "invoice_number",
    "invoice_date",
    "due_date",
    "vendor_name",
    "customer_name",
    "subtotal",
    "tax_amount",
    "total_amount",
    "currency",
}


@pytest.fixture
def review_context(tmp_path, monkeypatch):
    """
    Create an isolated database, document and completed processing attempt.

    Each test receives its own database so tests cannot affect one another.
    """

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

    complete_processing_attempt(
        attempt_id=attempt["attempt_id"],
        status="completed",
    )

    return {
        "document": document,
        "attempt": attempt,
    }


def sample_extraction():
    """Return a representative immutable extraction snapshot."""

    return {
        "invoice_extraction": {
            "document_type": "invoice",
            "fields": {
                "invoice_number": {
                    "value": "INV-1001",
                    "normalized_value": "INV-1001",
                    "source": "rule_based",
                    "references": [
                        {
                            "type": "page",
                            "page_number": 1,
                        }
                    ],
                    "evidence": [],
                    "review_status": "pending",
                },
                "total_amount": {
                    "value": "1200.00",
                    "normalized_value": "1200.00",
                    "source": "rule_based",
                    "references": [
                        {
                            "type": "page",
                            "page_number": 1,
                        }
                    ],
                    "evidence": [],
                    "review_status": "pending",
                },
            },
        }
    }


def test_save_and_retrieve_attempt_extraction_snapshot(review_context):
    """A successful attempt's complete extraction can be retrieved."""

    attempt_id = review_context["attempt"]["attempt_id"]
    extraction = sample_extraction()

    processing_repository.save_processing_attempt_result(
        attempt_id=attempt_id,
        extraction_data=extraction,
    )

    saved = processing_repository.get_processing_attempt_result(attempt_id)

    assert saved is not None
    assert saved["attempt_id"] == attempt_id
    assert saved["extracted_data"] == extraction
    assert saved["created_at"]


def test_attempt_extraction_snapshot_cannot_be_overwritten(review_context):
    """An attempt cannot silently replace its original extraction snapshot."""

    attempt_id = review_context["attempt"]["attempt_id"]

    original_extraction = sample_extraction()

    processing_repository.save_processing_attempt_result(
        attempt_id=attempt_id,
        extraction_data=original_extraction,
    )

    replacement_extraction = {
        "invoice_extraction": {
            "document_type": "unknown",
            "fields": {},
        }
    }

    with pytest.raises(sqlite3.IntegrityError):
        processing_repository.save_processing_attempt_result(
            attempt_id=attempt_id,
            extraction_data=replacement_extraction,
        )

    saved = processing_repository.get_processing_attempt_result(attempt_id)

    assert saved["extracted_data"] == original_extraction


def test_snapshot_cannot_reference_nonexistent_attempt(review_context):
    """Foreign-key constraints must reject unknown processing attempts."""

    with pytest.raises(sqlite3.IntegrityError):
        processing_repository.save_processing_attempt_result(
            attempt_id="nonexistent-attempt",
            extraction_data=sample_extraction(),
        )


def test_record_approved_field(review_context):
    """An approval records the review decision without a replacement value."""

    attempt_id = review_context["attempt"]["attempt_id"]

    processing_repository.save_processing_attempt_result(
        attempt_id=attempt_id,
        extraction_data=sample_extraction(),
    )

    review_id = processing_repository.record_invoice_field_review(
        attempt_id=attempt_id,
        field_name="invoice_number",
        decision="approved",
        reviewer_id=None,
    )

    reviews = processing_repository.get_invoice_field_reviews(attempt_id)

    assert len(reviews) == 1
    assert reviews[0]["review_id"] == review_id
    assert reviews[0]["field_name"] == "invoice_number"
    assert reviews[0]["decision"] == "approved"
    assert reviews[0]["corrected_value"] is None


def test_record_corrected_field(review_context):
    """A correction preserves the replacement value and its JSON type."""

    attempt_id = review_context["attempt"]["attempt_id"]

    processing_repository.save_processing_attempt_result(
        attempt_id=attempt_id,
        extraction_data=sample_extraction(),
    )

    review_id = processing_repository.record_invoice_field_review(
        attempt_id=attempt_id,
        field_name="total_amount",
        decision="corrected",
        corrected_value=1250.50,
        reviewer_id=None,
    )

    reviews = processing_repository.get_invoice_field_reviews(attempt_id)

    assert len(reviews) == 1
    assert reviews[0]["review_id"] == review_id
    assert reviews[0]["decision"] == "corrected"
    assert reviews[0]["corrected_value"] == 1250.50
    assert isinstance(reviews[0]["corrected_value"], float)


def test_record_rejected_field(review_context):
    """A rejection records no replacement value."""

    attempt_id = review_context["attempt"]["attempt_id"]

    processing_repository.save_processing_attempt_result(
        attempt_id=attempt_id,
        extraction_data=sample_extraction(),
    )

    processing_repository.record_invoice_field_review(
        attempt_id=attempt_id,
        field_name="total_amount",
        decision="rejected",
    )

    reviews = processing_repository.get_invoice_field_reviews(attempt_id)

    assert len(reviews) == 1
    assert reviews[0]["decision"] == "rejected"
    assert reviews[0]["corrected_value"] is None


def test_correction_requires_replacement_value(review_context):
    """A correction without a replacement value must be rejected."""

    attempt_id = review_context["attempt"]["attempt_id"]

    processing_repository.save_processing_attempt_result(
        attempt_id=attempt_id,
        extraction_data=sample_extraction(),
    )

    with pytest.raises(ValueError):
        processing_repository.record_invoice_field_review(
            attempt_id=attempt_id,
            field_name="total_amount",
            decision="corrected",
        )


@pytest.mark.parametrize("decision", ["approved", "rejected"])
def test_non_correction_decision_cannot_have_replacement_value(
    review_context,
    decision,
):
    """Only a corrected decision may contain a replacement value."""

    attempt_id = review_context["attempt"]["attempt_id"]

    processing_repository.save_processing_attempt_result(
        attempt_id=attempt_id,
        extraction_data=sample_extraction(),
    )

    with pytest.raises(ValueError):
        processing_repository.record_invoice_field_review(
            attempt_id=attempt_id,
            field_name="total_amount",
            decision=decision,
            corrected_value=1250.50,
        )


def test_unsupported_invoice_field_is_rejected(review_context):
    """Only the nine supported invoice fields can be reviewed."""

    attempt_id = review_context["attempt"]["attempt_id"]

    processing_repository.save_processing_attempt_result(
        attempt_id=attempt_id,
        extraction_data=sample_extraction(),
    )

    with pytest.raises(ValueError):
        processing_repository.record_invoice_field_review(
            attempt_id=attempt_id,
            field_name="supplier_address",
            decision="approved",
        )


def test_unsupported_review_decision_is_rejected(review_context):
    """Review decisions must be approved, corrected or rejected."""

    attempt_id = review_context["attempt"]["attempt_id"]

    processing_repository.save_processing_attempt_result(
        attempt_id=attempt_id,
        extraction_data=sample_extraction(),
    )

    with pytest.raises(ValueError):
        processing_repository.record_invoice_field_review(
            attempt_id=attempt_id,
            field_name="invoice_number",
            decision="pending",
        )


def test_multiple_review_events_are_preserved(review_context):
    """A later review event must not overwrite an earlier decision."""

    attempt_id = review_context["attempt"]["attempt_id"]

    processing_repository.save_processing_attempt_result(
        attempt_id=attempt_id,
        extraction_data=sample_extraction(),
    )

    first_review_id = processing_repository.record_invoice_field_review(
        attempt_id=attempt_id,
        field_name="total_amount",
        decision="approved",
    )

    second_review_id = processing_repository.record_invoice_field_review(
        attempt_id=attempt_id,
        field_name="total_amount",
        decision="corrected",
        corrected_value="1250.00",
    )

    history = processing_repository.get_invoice_field_reviews(attempt_id)

    assert len(history) == 2
    assert history[0]["review_id"] == first_review_id
    assert history[0]["decision"] == "approved"
    assert history[1]["review_id"] == second_review_id
    assert history[1]["decision"] == "corrected"
    assert history[1]["corrected_value"] == "1250.00"


def test_latest_review_is_retrieved_independently_per_field(review_context):
    """Each field's latest decision is independent of other fields."""

    attempt_id = review_context["attempt"]["attempt_id"]

    processing_repository.save_processing_attempt_result(
        attempt_id=attempt_id,
        extraction_data=sample_extraction(),
    )

    processing_repository.record_invoice_field_review(
        attempt_id=attempt_id,
        field_name="invoice_number",
        decision="approved",
    )

    processing_repository.record_invoice_field_review(
        attempt_id=attempt_id,
        field_name="total_amount",
        decision="approved",
    )

    processing_repository.record_invoice_field_review(
        attempt_id=attempt_id,
        field_name="total_amount",
        decision="corrected",
        corrected_value="1250.00",
    )

    latest = processing_repository.get_latest_invoice_field_reviews(attempt_id)

    assert set(latest.keys()) == {
        "invoice_number",
        "total_amount",
    }

    assert latest["invoice_number"]["decision"] == "approved"

    assert latest["total_amount"]["decision"] == "corrected"
    assert latest["total_amount"]["corrected_value"] == "1250.00"


def test_reviews_cannot_reference_nonexistent_attempt(review_context):
    """Review events must reference an existing extraction snapshot."""

    with pytest.raises(sqlite3.IntegrityError):
        processing_repository.record_invoice_field_review(
            attempt_id="nonexistent-attempt",
            field_name="invoice_number",
            decision="approved",
        )


def test_review_history_for_attempt_without_reviews_is_empty(review_context):
    """An attempt without reviewer activity has an empty review history."""

    attempt_id = review_context["attempt"]["attempt_id"]

    processing_repository.save_processing_attempt_result(
        attempt_id=attempt_id,
        extraction_data=sample_extraction(),
    )

    assert processing_repository.get_invoice_field_reviews(attempt_id) == []
    assert processing_repository.get_latest_invoice_field_reviews(attempt_id) == {}

def test_attempt_snapshot_cannot_be_deleted(review_context):
    """The original extraction snapshot must be retained."""

    import sqlite3
    import pytest

    from app.db.database import get_connection

    attempt_id = review_context["attempt"]["attempt_id"]

    with pytest.raises(
        sqlite3.IntegrityError,
        match="processing attempt results cannot be deleted",
    ):
        with get_connection() as connection:
            connection.execute(
                """
                DELETE FROM processing_attempt_results
                WHERE attempt_id = ?
                """,
                (attempt_id,),
            )


def test_invoice_review_event_cannot_be_deleted(review_context):
    """Human review history must be retained."""

    import sqlite3
    import pytest

    from app.db.database import get_connection
    from app.services.processing_repository import (
        record_invoice_field_review,
    )

    attempt_id = review_context["attempt"]["attempt_id"]

    review_id = record_invoice_field_review(
        attempt_id=attempt_id,
        field_name="invoice_number",
        decision="approved",
    )

    with pytest.raises(
        sqlite3.IntegrityError,
        match="invoice field reviews cannot be deleted",
    ):
        with get_connection() as connection:
            connection.execute(
                """
                DELETE FROM invoice_field_reviews
                WHERE review_id = ?
                """,
                (review_id,),
            )



def test_attempt_snapshot_cannot_be_deleted(review_context):
    """The original extraction snapshot must be retained."""

    import sqlite3
    import pytest

    from app.db.database import get_connection

    attempt_id = review_context["attempt"]["attempt_id"]
    processing_repository.save_processing_attempt_result(
        attempt_id=attempt_id,
        extraction_data=sample_extraction(),
    )

    with pytest.raises(
        sqlite3.IntegrityError,
        match="processing attempt results cannot be deleted",
    ):
        with get_connection() as connection:
            connection.execute(
                """
                DELETE FROM processing_attempt_results
                WHERE attempt_id = ?
                """,
                (attempt_id,),
            )


def test_invoice_review_event_cannot_be_deleted(review_context):
    """Human review history must be retained."""

    import sqlite3
    import pytest

    from app.db.database import get_connection
    from app.services.processing_repository import (
        record_invoice_field_review,
    )

    attempt_id = review_context["attempt"]["attempt_id"]
    processing_repository.save_processing_attempt_result(
        attempt_id=attempt_id,
        extraction_data=sample_extraction(),
    )
    review_id = record_invoice_field_review(
        attempt_id=attempt_id,
        field_name="invoice_number",
        decision="approved",
    )

    with pytest.raises(
        sqlite3.IntegrityError,
        match="invoice field reviews cannot be deleted",
    ):
        with get_connection() as connection:
            connection.execute(
                """
                DELETE FROM invoice_field_reviews
                WHERE review_id = ?
                """,
                (review_id,),
            )


def test_attempt_with_snapshot_cannot_be_deleted(review_context):
    """Cascade deletion must not silently remove an extraction snapshot."""

    import sqlite3
    import pytest

    from app.db.database import get_connection

    attempt_id = review_context["attempt"]["attempt_id"]
    processing_repository.save_processing_attempt_result(
        attempt_id=attempt_id,
        extraction_data=sample_extraction(),
    )
    with pytest.raises(
        sqlite3.IntegrityError,
        match="processing attempt results cannot be deleted",
    ):
        with get_connection() as connection:
            connection.execute(
                """
                DELETE FROM processing_attempts
                WHERE attempt_id = ?
                """,
                (attempt_id,),
            )