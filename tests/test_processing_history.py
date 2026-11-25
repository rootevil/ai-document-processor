import pytest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import sqlite3
from app.db.database import get_connection, initialize_database

from app.services.document_repository import (
    create_document_record,
)

from app.services.processing_repository import (
    DocumentAlreadyProcessingError,
    DocumentLifecycleError,
    save_processing_result,
    start_processing_attempt,
    complete_processing_attempt,
    get_processing_history,
    get_processing_result,
)


def create_test_document():
    """
    Create a sample document for processing history tests.
    """

    return create_document_record(
        original_filename="invoice.pdf",
        stored_filename="invoice.pdf",
        content_type="application/pdf",
        file_size=1024,
    )


def test_multiple_processing_attempts(tmp_path, monkeypatch):
    """
    Verify that multiple processing attempts are preserved.
    """

    monkeypatch.setattr(
        "app.db.database.settings.database_path",
        tmp_path / "document_ai.db",
    )

    initialize_database()

    document = create_test_document()

    # Create and complete the first attempt.
    first_attempt = start_processing_attempt(document.id)

    complete_processing_attempt(
        attempt_id=first_attempt["attempt_id"],
        status="completed",
    )

    # Create and fail the second attempt.
    second_attempt = start_processing_attempt(document.id)

    complete_processing_attempt(
        attempt_id=second_attempt["attempt_id"],
        status="failed",
        error_code="DOCUMENT_PROCESSING_FAILED",
        error_message="Invalid document contents",
    )

    # Retrieve the document's processing history.
    history = get_processing_history(document.id)

    assert len(history) == 2

    assert history[0]["attempt_number"] == 2
    assert history[1]["attempt_number"] == 1

    assert history[0]["status"] == "failed"
    assert history[1]["status"] == "completed"


def test_failed_attempt_does_not_replace_successful_result(
    tmp_path,
    monkeypatch,
):
    """
    Verify that failed attempts cannot overwrite
    previously saved successful extraction results.
    """

    monkeypatch.setattr(
        "app.db.database.settings.database_path",
        tmp_path / "document_ai.db",
    )

    initialize_database()

    document = create_test_document()

    successful_extraction = {
        "source_filename": "invoice.pdf",
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

    # Save the original successful extraction.
    save_processing_result(
        document_id=document.id,
        extraction_data=successful_extraction,
        status="completed",
        started_at="2026-11-25T10:00:00+00:00",
        completed_at="2026-11-25T10:00:05+00:00",
    )

    # Create a subsequent failed attempt.
    failed_attempt = start_processing_attempt(document.id)

    complete_processing_attempt(
        attempt_id=failed_attempt["attempt_id"],
        status="failed",
        error_code="DOCUMENT_PROCESSING_FAILED",
        error_message="Extraction failed",
    )

    # Retrieve the previously successful result.
    saved_result = get_processing_result(document.id)

    assert saved_result["status"] == "completed"

    assert saved_result["extracted_data"] == successful_extraction

    # Verify that the failure was separately recorded.
    history = get_processing_history(document.id)

    assert len(history) == 1
    assert history[0]["status"] == "failed"



def test_processing_attempt_numbers_increment(
    tmp_path,
    monkeypatch,
):
    """
    Verify that attempt numbers increment for each document.

    A document must finish its current processing attempt
    before another attempt can begin.
    """

    monkeypatch.setattr(
        "app.db.database.settings.database_path",
        tmp_path / "document_ai.db",
    )

    initialize_database()

    document = create_test_document()

    # Start the first processing attempt.
    first = start_processing_attempt(document.id)

    assert first["attempt_number"] == 1

    # Complete the first attempt.
    # This releases the active-processing restriction.
    complete_processing_attempt(
        attempt_id=first["attempt_id"],
        status="completed",
    )

    # Start another attempt for the same document.
    second = start_processing_attempt(document.id)

    # The second attempt should receive the next number.
    assert second["attempt_number"] == 2

    assert first["attempt_id"] != second["attempt_id"]

def test_cannot_start_second_active_attempt(
    tmp_path,
    monkeypatch,
):
    """A document can have only one active attempt at a time."""

    monkeypatch.setattr(
        "app.db.database.settings.database_path",
        tmp_path / "document_ai.db",
    )

    initialize_database()
    document = create_test_document()

    # The first attempt remains active while its status is "processing".
    first = start_processing_attempt(document.id)

    # A second request for that document must be rejected.
    with pytest.raises(DocumentAlreadyProcessingError):
        start_processing_attempt(document.id)

    # Finishing the first attempt releases the active slot.
    complete_processing_attempt(
        attempt_id=first["attempt_id"],
        status="completed",
    )

    # A later attempt can start and receives the next number.
    second = start_processing_attempt(document.id)
    assert second["attempt_number"] == 2


def test_cannot_process_document_in_invalid_lifecycle_state(
    tmp_path,
    monkeypatch,
):
    """Documents outside the allowed states cannot start an attempt."""

    monkeypatch.setattr(
        "app.db.database.settings.database_path",
        tmp_path / "document_ai.db",
    )

    initialize_database()
    document = create_test_document()

    # Simulate a stale processing status with no active attempt.
    with get_connection() as connection:
        connection.execute(
            "UPDATE documents SET status = ? WHERE id = ?",
            ("processing", document.id),
        )

    with pytest.raises(DocumentLifecycleError, match="cannot be processed"):
        start_processing_attempt(document.id)

    # The rejected transition must not create a history row.
    assert get_processing_history(document.id) == []


def test_concurrent_attempt_requests_create_only_one_active_attempt(
    tmp_path,
    monkeypatch,
):
    """Simultaneous callers cannot both start an active attempt."""

    monkeypatch.setattr(
        "app.db.database.settings.database_path",
        tmp_path / "document_ai.db",
    )

    initialize_database()
    document = create_test_document()
    barrier = Barrier(2)

    def try_start_attempt():
        barrier.wait()
        try:
            return start_processing_attempt(document.id)
        except DocumentAlreadyProcessingError as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: try_start_attempt(), range(2)))

    successful_attempts = [
        result for result in results
        if isinstance(result, dict)
    ]
    rejected_attempts = [
        result for result in results
        if isinstance(result, DocumentAlreadyProcessingError)
    ]

    assert len(successful_attempts) == 1
    assert len(rejected_attempts) == 1
    assert len(get_processing_history(document.id)) == 1

def test_processing_history_for_unknown_document(
    tmp_path,
    monkeypatch,
):
    """
    Verify that unknown documents return an empty history.
    """

    monkeypatch.setattr(
        "app.db.database.settings.database_path",
        tmp_path / "document_ai.db",
    )

    initialize_database()

    history = get_processing_history("unknown-document")

    assert history == []

def test_start_attempt_rolls_back_if_status_update_fails(
    tmp_path,
    monkeypatch,
):
    """A failed status update must roll back the inserted attempt."""

    monkeypatch.setattr(
        "app.db.database.settings.database_path",
        tmp_path / "document_ai.db",
    )

    initialize_database()
    document = create_test_document()

    # Force the document update to fail after the attempt is inserted.
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TRIGGER fail_processing_status_update
            BEFORE UPDATE OF status ON documents
            WHEN NEW.status = 'processing'
            BEGIN
                SELECT RAISE(ABORT, 'simulated status update failure');
            END;
            """
        )

    # The repository transaction should roll back the attempt insert.
    with pytest.raises(sqlite3.IntegrityError):
        start_processing_attempt(document.id)

    # No attempt should remain after the transaction rollback.
    assert get_processing_history(document.id) == []

    # The document should retain its original lifecycle status.
    with get_connection() as connection:
        row = connection.execute(
            "SELECT status FROM documents WHERE id = ?",
            (document.id,),
        ).fetchone()

    assert row["status"] == "uploaded"