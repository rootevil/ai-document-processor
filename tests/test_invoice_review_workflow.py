
"""
End-to-end tests for the invoice human-review workflow.

These tests verify the complete integration between:
1. Document processing.
2. Immutable extraction snapshot persistence.
3. Human review through the API.
4. Review-aware extraction.
5. Preservation of original evidence and provenance.

The extraction engine is mocked so that these tests focus on
the integration between our application components.
"""

from fastapi.testclient import TestClient

from app.db.database import initialize_database
from app.main import app

from app.services import document_processing_service
from app.services.document_repository import create_document_record

from app.services.processing_repository import (
    get_processing_attempt_result,
    get_invoice_field_reviews,
)


client = TestClient(app)


def test_complete_invoice_review_workflow(
    tmp_path,
    monkeypatch,
):
    """
    A processed invoice can be reviewed without changing its
    original machine-generated extraction.
    """

    # ---------------------------------------------------------
    # STEP 1: Initialize an isolated database.
    # ---------------------------------------------------------

    monkeypatch.setattr(
        "app.db.database.settings.database_path",
        tmp_path / "document_ai.db",
    )

    initialize_database()

    # ---------------------------------------------------------
    # STEP 2: Create a document record.
    # ---------------------------------------------------------

    document = create_document_record(
        original_filename="invoice.pdf",
        stored_filename="invoice.pdf",
        content_type="application/pdf",
        file_size=1024,
    )

    # ---------------------------------------------------------
    # STEP 3: Prepare representative extraction output.
    #
    # Include evidence and provenance so we can verify that
    # human review does not destroy extraction metadata.
    # ---------------------------------------------------------

    extraction = {
        "invoice_extraction": {
            "document_type": "invoice",
            "fields": {
                "invoice_number": {
                    "value": "INV-1001",
                    "normalized_value": "INV-1001",
                    "source": "rule_based",
                    "confidence": 0.98,
                    "validation_status": "valid",
                    "review_status": "pending",
                    "references": [
                        {
                            "type": "page",
                            "page_number": 1,
                        }
                    ],
                    "evidence": [
                        {
                            "text": "Invoice Number: INV-1001",
                            "reference": {
                                "type": "page",
                                "page_number": 1,
                            },
                        }
                    ],
                },
                "vendor_name": {
                    "value": "Original Vendor Ltd",
                    "normalized_value": "Original Vendor Ltd",
                    "source": "ai",
                    "confidence": 0.91,
                    "validation_status": "pending",
                    "review_status": "pending",
                    "references": [
                        {
                            "type": "page",
                            "page_number": 1,
                        }
                    ],
                    "evidence": [
                        {
                            "text": "Original Vendor Ltd",
                            "reference": {
                                "type": "page",
                                "page_number": 1,
                            },
                        }
                    ],
                },
                "total_amount": {
                    "value": 1200.00,
                    "normalized_value": 1200.00,
                    "source": "rule_based",
                    "confidence": 0.99,
                    "validation_status": "valid",
                    "review_status": "pending",
                    "references": [
                        {
                            "type": "page",
                            "page_number": 1,
                        }
                    ],
                    "evidence": [
                        {
                            "text": "Total: 1200.00",
                            "reference": {
                                "type": "page",
                                "page_number": 1,
                            },
                        }
                    ],
                },
            },
        }
    }

    # ---------------------------------------------------------
    # STEP 4: Mock only the extraction engine.
    #
    # The actual processing service and database operations
    # remain active during this test.
    # ---------------------------------------------------------

    monkeypatch.setattr(
        document_processing_service,
        "process_document",
        lambda file_path: extraction,
    )

    # ---------------------------------------------------------
    # STEP 5: Process and persist the document.
    # ---------------------------------------------------------

    processing_result = (
        document_processing_service.process_and_save_document(
            document_id=document.id,
            file_path=tmp_path / "invoice.pdf",
        )
    )

    assert processing_result["status"] == "completed"

    attempt_id = processing_result["attempt_id"]

    # ---------------------------------------------------------
    # STEP 6: Verify the immutable extraction snapshot.
    # ---------------------------------------------------------

    original_snapshot = get_processing_attempt_result(
        attempt_id
    )

    assert original_snapshot is not None

    assert (
        original_snapshot["extracted_data"]
        == extraction
    )

    # ---------------------------------------------------------
    # STEP 7: Submit a human correction through the API.
    # ---------------------------------------------------------

    review_response = client.post(
        (
            f"/api/v1/documents/{document.id}"
            f"/attempts/{attempt_id}/reviews"
        ),
        json={
            "field_name": "vendor_name",
            "decision": "corrected",
            "corrected_value": "Corrected Vendor Ltd",
        },
    )

    assert review_response.status_code == 201

    review = review_response.json()

    assert review["field_name"] == "vendor_name"
    assert review["decision"] == "corrected"
    assert review["corrected_value"] == "Corrected Vendor Ltd"

    # ---------------------------------------------------------
    # STEP 8: Verify that the review event was persisted.
    # ---------------------------------------------------------

    review_history = get_invoice_field_reviews(
        attempt_id
    )

    assert len(review_history) == 1

    assert review_history[0]["field_name"] == "vendor_name"
    assert review_history[0]["decision"] == "corrected"

    # ---------------------------------------------------------
    # STEP 9: Retrieve the review-aware extraction through API.
    # ---------------------------------------------------------

    effective_response = client.get(
        (
            f"/api/v1/documents/{document.id}"
            f"/attempts/{attempt_id}/review-aware-extraction"
        )
    )

    assert effective_response.status_code == 200

    effective_result = effective_response.json()

    assert effective_result["document_id"] == document.id
    assert effective_result["attempt_id"] == attempt_id

    fields = effective_result["fields"]

    # ---------------------------------------------------------
    # STEP 10: Verify original and effective values.
    # ---------------------------------------------------------

    vendor = fields["vendor_name"]

    assert vendor["original_value"] == "Original Vendor Ltd"

    assert vendor["effective_value"] == "Corrected Vendor Ltd"

    assert vendor["review_status"] == "corrected"

    # ---------------------------------------------------------
    # STEP 11: Verify extraction metadata is preserved.
    # ---------------------------------------------------------

    assert vendor["normalized_value"] == "Original Vendor Ltd"

    assert vendor["source"] == "ai"

    assert vendor["confidence"] == 0.91

    assert vendor["validation_status"] == "pending"

    assert vendor["references"] == [
        {
            "type": "page",
            "page_number": 1,
        }
    ]

    assert vendor["evidence"] == [
        {
            "text": "Original Vendor Ltd",
            "reference": {
                "type": "page",
                "page_number": 1,
            },
        }
    ]

    # ---------------------------------------------------------
    # STEP 12: Verify other fields remain independent.
    # ---------------------------------------------------------

    invoice_number = fields["invoice_number"]

    assert invoice_number["original_value"] == "INV-1001"

    assert invoice_number["effective_value"] == "INV-1001"

    assert invoice_number["review_status"] == "pending"

    total_amount = fields["total_amount"]

    assert total_amount["original_value"] == 1200.00

    assert total_amount["effective_value"] == 1200.00

    assert total_amount["review_status"] == "pending"

    # ---------------------------------------------------------
    # STEP 13: Verify the original snapshot was never modified.
    # ---------------------------------------------------------

    saved_snapshot = get_processing_attempt_result(
        attempt_id
    )

    assert saved_snapshot["extracted_data"] == extraction

    assert (
        saved_snapshot["extracted_data"]
        ["invoice_extraction"]["fields"]["vendor_name"]["value"]
        == "Original Vendor Ltd"
    )


def test_multiple_field_decisions_preserve_complete_review_history(
    tmp_path,
    monkeypatch,
):
    """
    Multiple field decisions and repeated corrections must preserve
    review history while exposing only the latest decision per field.
    """

    monkeypatch.setattr(
        "app.db.database.settings.database_path",
        tmp_path / "document_ai.db",
    )

    initialize_database()

    document = create_document_record(
        original_filename="multi-review.pdf",
        stored_filename="multi-review.pdf",
        content_type="application/pdf",
        file_size=2048,
    )

    extraction = {
        "invoice_extraction": {
            "document_type": "invoice",
            "fields": {
                "invoice_number": {
                    "value": "INV-5001",
                    "normalized_value": "INV-5001",
                    "source": "rule_based",
                    "review_status": "pending",
                },
                "vendor_name": {
                    "value": "Old Vendor",
                    "normalized_value": "Old Vendor",
                    "source": "ai",
                    "review_status": "pending",
                    "evidence": [{"text": "Old Vendor"}],
                },
                "total_amount": {
                    "value": 5000.00,
                    "normalized_value": 5000.00,
                    "source": "rule_based",
                    "review_status": "pending",
                },
            },
        }
    }

    monkeypatch.setattr(
        document_processing_service,
        "process_document",
        lambda file_path: extraction,
    )

    processing_result = (
        document_processing_service.process_and_save_document(
            document_id=document.id,
            file_path=tmp_path / "multi-review.pdf",
        )
    )

    attempt_id = processing_result["attempt_id"]

    review_url = (
        f"/api/v1/documents/{document.id}"
        f"/attempts/{attempt_id}/reviews"
    )

    # First field: approve the original invoice number.
    approved_response = client.post(
        review_url,
        json={
            "field_name": "invoice_number",
            "decision": "approved",
        },
    )

    assert approved_response.status_code == 201

    # Second field: correct the vendor name.
    first_correction = client.post(
        review_url,
        json={
            "field_name": "vendor_name",
            "decision": "corrected",
            "corrected_value": "Correct Vendor",
        },
    )

    assert first_correction.status_code == 201

    # Repeat the correction with a more accurate value.
    second_correction = client.post(
        review_url,
        json={
            "field_name": "vendor_name",
            "decision": "corrected",
            "corrected_value": "Correct Vendor Limited",
        },
    )

    assert second_correction.status_code == 201

    # Third field: reject the extracted total amount.
    rejected_response = client.post(
        review_url,
        json={
            "field_name": "total_amount",
            "decision": "rejected",
        },
    )

    assert rejected_response.status_code == 201

    # Retrieve every review event.
    history_response = client.get(review_url)

    assert history_response.status_code == 200

    history = history_response.json()

    assert history["total_reviews"] == 4

    assert [
        (item["field_name"], item["decision"])
        for item in history["reviews"]
    ] == [
        ("invoice_number", "approved"),
        ("vendor_name", "corrected"),
        ("vendor_name", "corrected"),
        ("total_amount", "rejected"),
    ]

    # Retrieve only the latest decision for each field.
    latest_response = client.get(
        review_url + "/latest"
    )

    assert latest_response.status_code == 200

    latest = latest_response.json()

    assert latest["total_fields_reviewed"] == 3

    assert (
        latest["reviews"]["invoice_number"]["decision"]
        == "approved"
    )

    assert (
        latest["reviews"]["vendor_name"]["corrected_value"]
        == "Correct Vendor Limited"
    )

    assert (
        latest["reviews"]["total_amount"]["decision"]
        == "rejected"
    )

    # Retrieve the effective extraction.
    effective_response = client.get(
        (
            f"/api/v1/documents/{document.id}"
            f"/attempts/{attempt_id}/review-aware-extraction"
        )
    )

    assert effective_response.status_code == 200

    fields = effective_response.json()["fields"]

    # Approval retains the original prediction.
    assert fields["invoice_number"]["effective_value"] == "INV-5001"
    assert fields["invoice_number"]["review_status"] == "approved"

    # The latest correction becomes effective.
    assert fields["vendor_name"]["original_value"] == "Old Vendor"
    assert (
        fields["vendor_name"]["effective_value"]
        == "Correct Vendor Limited"
    )
    assert fields["vendor_name"]["review_status"] == "corrected"

    # Rejection removes the effective prediction.
    assert fields["total_amount"]["original_value"] == 5000.00
    assert fields["total_amount"]["effective_value"] is None
    assert fields["total_amount"]["review_status"] == "rejected"

    # Earlier correction events must remain in history.
    assert len(history["reviews"]) == 4

    # Original machine extraction must remain untouched.
    original_snapshot = get_processing_attempt_result(attempt_id)

    original_fields = (
        original_snapshot["extracted_data"]
        ["invoice_extraction"]["fields"]
    )

    assert original_fields["vendor_name"]["value"] == "Old Vendor"
    assert original_fields["total_amount"]["value"] == 5000.00


def test_reviews_are_isolated_between_processing_attempts(
    tmp_path,
    monkeypatch,
):
    """
    Human decisions for one processing attempt must not affect
    another attempt belonging to the same document.
    """

    monkeypatch.setattr(
        "app.db.database.settings.database_path",
        tmp_path / "document_ai.db",
    )

    initialize_database()

    document = create_document_record(
        original_filename="reprocessed-invoice.pdf",
        stored_filename="reprocessed-invoice.pdf",
        content_type="application/pdf",
        file_size=2048,
    )

    first_extraction = {
        "invoice_extraction": {
            "document_type": "invoice",
            "fields": {
                "invoice_number": {
                    "value": "INV-1001",
                    "normalized_value": "INV-1001",
                    "source": "rule_based",
                },
            },
        },
    }

    second_extraction = {
        "invoice_extraction": {
            "document_type": "invoice",
            "fields": {
                "invoice_number": {
                    "value": "INV-2002",
                    "normalized_value": "INV-2002",
                    "source": "rule_based",
                },
            },
        },
    }

    extractions = iter([
        first_extraction,
        second_extraction,
    ])

    monkeypatch.setattr(
        document_processing_service,
        "process_document",
        lambda file_path: next(extractions),
    )

    # Process the document for the first time.
    first_result = (
        document_processing_service.process_and_save_document(
            document_id=document.id,
            file_path=tmp_path / "reprocessed-invoice.pdf",
        )
    )

    first_attempt_id = first_result["attempt_id"]

    # Process the same document again.
    second_result = (
        document_processing_service.process_and_save_document(
            document_id=document.id,
            file_path=tmp_path / "reprocessed-invoice.pdf",
        )
    )

    second_attempt_id = second_result["attempt_id"]

    assert first_attempt_id != second_attempt_id

    # Correct the invoice number in the first attempt.
    first_review_url = (
        f"/api/v1/documents/{document.id}"
        f"/attempts/{first_attempt_id}/reviews"
    )

    review_response = client.post(
        first_review_url,
        json={
            "field_name": "invoice_number",
            "decision": "corrected",
            "corrected_value": "INV-1001-CORRECTED",
        },
    )

    assert review_response.status_code == 201

    # Retrieve the first attempt's review-aware extraction.
    first_effective_response = client.get(
        (
            f"/api/v1/documents/{document.id}"
            f"/attempts/{first_attempt_id}/review-aware-extraction"
        )
    )

    assert first_effective_response.status_code == 200

    first_fields = first_effective_response.json()["fields"]

    assert (
        first_fields["invoice_number"]["effective_value"]
        == "INV-1001-CORRECTED"
    )

    # Retrieve the second attempt's review-aware extraction.
    second_effective_response = client.get(
        (
            f"/api/v1/documents/{document.id}"
            f"/attempts/{second_attempt_id}/review-aware-extraction"
        )
    )

    assert second_effective_response.status_code == 200

    second_fields = second_effective_response.json()["fields"]

    # The second attempt must retain its own original value.
    assert (
        second_fields["invoice_number"]["original_value"]
        == "INV-2002"
    )

    assert (
        second_fields["invoice_number"]["effective_value"]
        == "INV-2002"
    )

    assert (
        second_fields["invoice_number"]["review_status"]
        == "pending"
    )

    # The second attempt must have no review events.
    second_history_url = (
        f"/api/v1/documents/{document.id}"
        f"/attempts/{second_attempt_id}/reviews"
    )

    second_history_response = client.get(second_history_url)

    assert second_history_response.status_code == 200
    assert second_history_response.json()["total_reviews"] == 0

    # The first attempt's review history remains intact.
    first_history_response = client.get(first_review_url)

    assert first_history_response.status_code == 200
    assert first_history_response.json()["total_reviews"] == 1
