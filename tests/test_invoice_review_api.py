import pytest

from fastapi.testclient import TestClient

from app.db.database import initialize_database
from app.main import app
from app.services.document_repository import create_document_record
from app.services.processing_repository import (
    start_processing_attempt,
    complete_processing_attempt,
    save_processing_attempt_result,
)


client = TestClient(app)


def create_review_context(tmp_path, monkeypatch):
    """Create an isolated database with a completed extraction attempt."""

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
                    "review_status": "pending",
                },
                "total_amount": {
                    "value": 1200.00,
                    "normalized_value": 1200.00,
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

    return document, attempt, extraction


def review_url(document_id, attempt_id, suffix=""):
    """Build a URL for an attempt-specific review endpoint."""

    return (
        f"/api/v1/documents/{document_id}"
        f"/attempts/{attempt_id}/reviews{suffix}"
    )


def test_retrieve_original_attempt_extraction(
    tmp_path,
    monkeypatch,
):
    """The API must return the original immutable extraction."""

    document, attempt, extraction = create_review_context(
        tmp_path,
        monkeypatch,
    )

    response = client.get(
        f"/api/v1/documents/{document.id}"
        f"/attempts/{attempt['attempt_id']}/extraction"
    )

    assert response.status_code == 200

    result = response.json()

    assert result["attempt_id"] == attempt["attempt_id"]
    assert result["extracted_data"] == extraction
    assert result["created_at"] is not None


def test_submit_approved_field_review(
    tmp_path,
    monkeypatch,
):
    """A reviewer must be able to approve an extracted field."""

    document, attempt, extraction = create_review_context(
        tmp_path,
        monkeypatch,
    )

    response = client.post(
        review_url(document.id, attempt["attempt_id"]),
        json={
            "field_name": "invoice_number",
            "decision": "approved",
        },
    )

    assert response.status_code == 201

    result = response.json()

    assert result["attempt_id"] == attempt["attempt_id"]
    assert result["field_name"] == "invoice_number"
    assert result["decision"] == "approved"
    assert result["corrected_value"] is None
    assert result["review_id"] is not None


def test_submit_corrected_field_review(
    tmp_path,
    monkeypatch,
):
    """A corrected value must be stored separately from the prediction."""

    document, attempt, extraction = create_review_context(
        tmp_path,
        monkeypatch,
    )

    response = client.post(
        review_url(document.id, attempt["attempt_id"]),
        json={
            "field_name": "total_amount",
            "decision": "corrected",
            "corrected_value": 1250.50,
        },
    )

    assert response.status_code == 201

    result = response.json()

    assert result["decision"] == "corrected"
    assert result["corrected_value"] == 1250.50

    # The original machine extraction must remain unchanged.
    extraction_response = client.get(
        f"/api/v1/documents/{document.id}"
        f"/attempts/{attempt['attempt_id']}/extraction"
    )

    original_value = (
        extraction_response.json()["extracted_data"]
        ["invoice_extraction"]["fields"]["total_amount"]["value"]
    )

    assert original_value == 1200.00


def test_submit_rejected_field_review(
    tmp_path,
    monkeypatch,
):
    """A reviewer must be able to reject a prediction."""

    document, attempt, extraction = create_review_context(
        tmp_path,
        monkeypatch,
    )

    response = client.post(
        review_url(document.id, attempt["attempt_id"]),
        json={
            "field_name": "invoice_number",
            "decision": "rejected",
        },
    )

    assert response.status_code == 201
    assert response.json()["decision"] == "rejected"


def test_corrected_review_requires_replacement_value(
    tmp_path,
    monkeypatch,
):
    """A correction without a replacement value must be rejected."""

    document, attempt, extraction = create_review_context(
        tmp_path,
        monkeypatch,
    )

    response = client.post(
        review_url(document.id, attempt["attempt_id"]),
        json={
            "field_name": "total_amount",
            "decision": "corrected",
        },
    )

    assert response.status_code == 422


def test_invalid_review_field_is_rejected(
    tmp_path,
    monkeypatch,
):
    """Only the nine supported invoice fields can be reviewed."""

    document, attempt, extraction = create_review_context(
        tmp_path,
        monkeypatch,
    )

    response = client.post(
        review_url(document.id, attempt["attempt_id"]),
        json={
            "field_name": "supplier_address",
            "decision": "approved",
        },
    )

    assert response.status_code == 422


def test_retrieve_complete_review_history_and_latest_decisions(
    tmp_path,
    monkeypatch,
):
    """The API must expose both review history and latest decisions."""

    document, attempt, extraction = create_review_context(
        tmp_path,
        monkeypatch,
    )

    base_url = review_url(document.id, attempt["attempt_id"])

    # First decision for invoice number.
    first_response = client.post(
        base_url,
        json={
            "field_name": "invoice_number",
            "decision": "approved",
        },
    )

    assert first_response.status_code == 201

    # A later correction becomes the latest decision.
    second_response = client.post(
        base_url,
        json={
            "field_name": "invoice_number",
            "decision": "corrected",
            "corrected_value": "INV-1002",
        },
    )

    assert second_response.status_code == 201

    # Another field receives its own decision.
    third_response = client.post(
        base_url,
        json={
            "field_name": "total_amount",
            "decision": "approved",
        },
    )

    assert third_response.status_code == 201

    # Retrieve the complete chronological history.
    history_response = client.get(base_url)

    assert history_response.status_code == 200

    history = history_response.json()

    assert history["total_reviews"] == 3
    assert len(history["reviews"]) == 3

    assert [
        item["decision"] for item in history["reviews"]
    ] == ["approved", "corrected", "approved"]

    # Retrieve the latest decision independently for each field.
    latest_response = client.get(
        base_url + "/latest"
    )

    assert latest_response.status_code == 200

    latest = latest_response.json()

    assert latest["total_fields_reviewed"] == 2

    assert (
        latest["reviews"]["invoice_number"]["decision"]
        == "corrected"
    )

    assert (
        latest["reviews"]["invoice_number"]["corrected_value"]
        == "INV-1002"
    )

    assert (
        latest["reviews"]["total_amount"]["decision"]
        == "approved"
    )


def test_attempt_cannot_be_accessed_through_another_document(
    tmp_path,
    monkeypatch,
):
    """An attempt must belong to the document in the URL."""

    document, attempt, extraction = create_review_context(
        tmp_path,
        monkeypatch,
    )

    other_document = create_document_record(
        original_filename="another.pdf",
        stored_filename="another.pdf",
        content_type="application/pdf",
        file_size=1024,
    )

    response = client.get(
        f"/api/v1/documents/{other_document.id}"
        f"/attempts/{attempt['attempt_id']}/extraction"
    )

    assert response.status_code == 404


def test_review_endpoint_rejects_nonexistent_document(
    tmp_path,
    monkeypatch,
):
    """Review operations must verify that the document exists."""

    document, attempt, extraction = create_review_context(
        tmp_path,
        monkeypatch,
    )

    response = client.post(
        review_url("nonexistent-document", attempt["attempt_id"]),
        json={
            "field_name": "invoice_number",
            "decision": "approved",
        },
    )

    assert response.status_code == 404


def test_review_endpoint_rejects_nonexistent_attempt(
    tmp_path,
    monkeypatch,
):
    """Review operations must reject unknown processing attempts."""

    document, attempt, extraction = create_review_context(
        tmp_path,
        monkeypatch,
    )

    response = client.post(
        review_url(document.id, "nonexistent-attempt"),
        json={
            "field_name": "invoice_number",
            "decision": "approved",
        },
    )

    assert response.status_code == 404
