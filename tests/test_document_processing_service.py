import pytest

from app.db.database import initialize_database
from app.services import document_processing_service as processing_service
from app.services.document_repository import create_document_record
from app.services.processing_repository import (
    get_processing_attempt_result,
    get_processing_history,
    get_processing_result,
)


def create_test_document():
    """Create a document record for processing-service tests."""

    return create_document_record(
        original_filename="invoice.pdf",
        stored_filename="invoice.pdf",
        content_type="application/pdf",
        file_size=1024,
    )


def setup_test_database(tmp_path, monkeypatch):
    """Initialize an isolated SQLite database for each test."""

    monkeypatch.setattr(
        "app.db.database.settings.database_path",
        tmp_path / "document_ai.db",
    )

    initialize_database()

    return create_test_document()


def test_successful_processing_saves_attempt_snapshot(
    tmp_path,
    monkeypatch,
):
    """A successful attempt must save its extraction snapshot."""

    document = setup_test_database(tmp_path, monkeypatch)

    extraction = {
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

    monkeypatch.setattr(
        processing_service,
        "process_document",
        lambda file_path: extraction,
    )

    result = processing_service.process_and_save_document(
        document_id=document.id,
        file_path=tmp_path / "invoice.pdf",
    )

    # The processing service should return the completed attempt.
    assert result["status"] == "completed"

    # The attempt-specific snapshot must preserve the extraction.
    snapshot = get_processing_attempt_result(result["attempt_id"])

    assert snapshot is not None
    assert snapshot["attempt_id"] == result["attempt_id"]
    assert snapshot["extracted_data"] == extraction

    # The existing latest-result interface must continue working.
    latest_result = get_processing_result(document.id)

    assert latest_result is not None
    assert latest_result["extracted_data"] == extraction

    # The processing history must identify the attempt as completed.
    history = get_processing_history(document.id)

    assert len(history) == 1
    assert history[0]["attempt_id"] == result["attempt_id"]
    assert history[0]["status"] == "completed"


def test_multiple_attempts_keep_separate_extraction_snapshots(
    tmp_path,
    monkeypatch,
):
    """A later attempt must not overwrite an earlier attempt snapshot."""

    document = setup_test_database(tmp_path, monkeypatch)

    first_extraction = {
        "file_type": "pdf",
        "invoice_number": "INV-1001",
    }

    second_extraction = {
        "file_type": "pdf",
        "invoice_number": "INV-2002",
    }

    extractions = iter([
        first_extraction,
        second_extraction,
    ])

    monkeypatch.setattr(
        processing_service,
        "process_document",
        lambda file_path: next(extractions),
    )

    first_result = processing_service.process_and_save_document(
        document_id=document.id,
        file_path=tmp_path / "invoice.pdf",
    )

    second_result = processing_service.process_and_save_document(
        document_id=document.id,
        file_path=tmp_path / "invoice.pdf",
    )

    first_snapshot = get_processing_attempt_result(
        first_result["attempt_id"]
    )

    second_snapshot = get_processing_attempt_result(
        second_result["attempt_id"]
    )

    assert first_result["attempt_id"] != second_result["attempt_id"]

    assert first_snapshot["extracted_data"] == first_extraction
    assert second_snapshot["extracted_data"] == second_extraction

    # The document-level result remains the latest successful result.
    latest_result = get_processing_result(document.id)

    assert latest_result["extracted_data"] == second_extraction

    history = get_processing_history(document.id)

    assert len(history) == 2
    assert history[0]["attempt_number"] == 2
    assert history[1]["attempt_number"] == 1


def test_failed_extraction_does_not_save_attempt_snapshot(
    tmp_path,
    monkeypatch,
):
    """An extraction failure must not create a successful snapshot."""

    document = setup_test_database(tmp_path, monkeypatch)

    def fail_extraction(file_path):
        raise ValueError("Simulated extraction failure")

    monkeypatch.setattr(
        processing_service,
        "process_document",
        fail_extraction,
    )

    with pytest.raises(ValueError, match="Simulated extraction failure"):
        processing_service.process_and_save_document(
            document_id=document.id,
            file_path=tmp_path / "invoice.pdf",
        )

    history = get_processing_history(document.id)

    assert len(history) == 1
    assert history[0]["status"] == "failed"

    snapshot = get_processing_attempt_result(
        history[0]["attempt_id"]
    )

    assert snapshot is None

    # A failed first attempt must not create a successful result.
    assert get_processing_result(document.id) is None


def test_snapshot_persistence_failure_marks_attempt_failed(
    tmp_path,
    monkeypatch,
):
    """A snapshot write failure must not leave an attempt completed."""

    document = setup_test_database(tmp_path, monkeypatch)

    extraction = {
        "file_type": "pdf",
        "invoice_number": "INV-3003",
    }

    monkeypatch.setattr(
        processing_service,
        "process_document",
        lambda file_path: extraction,
    )

    def fail_snapshot_save(attempt_id, extraction_data):
        raise RuntimeError("Simulated snapshot database failure")

    # The function is introduced in this chunk. Allow the test to
    # define the expected dependency before production imports it.
    monkeypatch.setattr(
        processing_service,
        "save_processing_attempt_result",
        fail_snapshot_save,
        raising=False,
    )

    with pytest.raises(
        RuntimeError,
        match="Simulated snapshot database failure",
    ):
        processing_service.process_and_save_document(
            document_id=document.id,
            file_path=tmp_path / "invoice.pdf",
        )

    history = get_processing_history(document.id)

    assert len(history) == 1
    assert history[0]["status"] == "failed"

    # The latest successful result must not be updated if snapshot
    # persistence fails first.
    assert get_processing_result(document.id) is None

    assert get_processing_attempt_result(
        history[0]["attempt_id"]
    ) is None
