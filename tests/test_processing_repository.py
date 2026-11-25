
import pytest

from app.db.database import initialize_database

from app.services.processing_repository import (
    update_document_status,
    save_processing_result,
    get_processing_result,
    start_processing_attempt,
    complete_processing_attempt,
    get_processing_history,
)

from app.services.document_repository import (
    create_document_record,
)

from app.services.processing_repository import (
    update_document_status,
    save_processing_result,
    get_processing_result,
)


def test_save_and_retrieve_processing_result(
    tmp_path,
    monkeypatch,
):
    # Use a temporary database so the test doesn't
    # modify the application's actual database.
    monkeypatch.setattr(
        "app.db.database.settings.database_path",
        tmp_path / "document_ai.db",
    )

    initialize_database()

    # Create a document record first.
    # The processing_results table references documents.
    document = create_document_record(
        original_filename="invoice.pdf",
        stored_filename="sample_invoice.pdf",
        content_type="application/pdf",
        file_size=1024,
    )

    extraction_data = {
        "source_filename": "sample_invoice.pdf",
        "file_type": "pdf",
        "sections": [
            {
                "section_type": "page",
                "section_name": "1",
                "content": {
                    "text": "Invoice Number: INV-1001"
                },
            }
        ],
    }

    # Save the processing result.
    save_processing_result(
        document_id=document.id,
        extraction_data=extraction_data,
        status="completed",
        started_at="2026-11-24T10:00:00+00:00",
        completed_at="2026-11-24T10:00:05+00:00",
    )

    # Retrieve the result from SQLite.
    result = get_processing_result(document.id)

    assert result is not None

    assert result["status"] == "completed"

    assert result["extracted_data"] == extraction_data

    assert result["error_message"] is None

    
def test_save_failed_processing_result(
    tmp_path,
    monkeypatch,
):
    # Use a temporary database for test isolation.
    monkeypatch.setattr(
        "app.db.database.settings.database_path",
        tmp_path / "document_ai.db",
    )

    initialize_database()

    # Create a document record first.
    document = create_document_record(
        original_filename="invalid.pdf",
        stored_filename="invalid.pdf",
        content_type="application/pdf",
        file_size=100,
    )

    # Start a new processing attempt.
    attempt = start_processing_attempt(
        document.id
    )

    # Mark the attempt as failed.
    complete_processing_attempt(
        attempt_id=attempt["attempt_id"],
        status="failed",
        error_code="DOCUMENT_PROCESSING_FAILED",
        error_message="Unable to extract PDF",
    )

    # Failed attempts should not appear as successful
    # extraction results.
    result = get_processing_result(document.id)

    assert result is None

    # The failure should instead be available
    # through the processing history.
    history = get_processing_history(document.id)

    assert len(history) == 1

    assert history[0]["status"] == "failed"

    assert (
        history[0]["error_message"]
        == "Unable to extract PDF"
    )

    assert (
        history[0]["error_code"]
        == "DOCUMENT_PROCESSING_FAILED"
    )



def test_update_document_status(
    tmp_path,
    monkeypatch,
):
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

    update_document_status(
        document.id,
        "processing",
    )

    from app.services.document_repository import (
        get_document_record,
    )

    updated_document = get_document_record(document.id)

    assert updated_document.status == "processing"


def test_processing_result_does_not_exist(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        "app.db.database.settings.database_path",
        tmp_path / "document_ai.db",
    )

    initialize_database()

    result = get_processing_result(
        "nonexistent-document"
    )

    assert result is None
