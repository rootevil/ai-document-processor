
from datetime import datetime, timezone
from pathlib import Path

from app.document_processing.document_processor import (
    process_document,
    DocumentProcessingError,
)

from app.services.processing_repository import (
    update_document_status,
    save_processing_result,
    start_processing_attempt,
    complete_processing_attempt,
)


def process_and_save_document(
    document_id: str,
    file_path: Path,
) -> dict:
    """
    Process a document and persist its successful extraction.

    This service coordinates the complete processing lifecycle.

    Responsibilities:
    1. Create a new processing attempt.
    2. Mark the document as processing.
    3. Extract document contents.
    4. Save successful extraction results.
    5. Record processing failures without deleting
       previously successful extraction results.
    """

    # STEP 1:
    # Create a new historical processing attempt.
    #
    # Every execution receives a unique attempt ID.
    attempt = start_processing_attempt(document_id)

    attempt_id = attempt["attempt_id"]

    started_at = attempt["started_at"]

    # STEP 2:
    # Update the original document's current status.
    update_document_status(
        document_id,
        "processing",
    )

    try:

        # STEP 3:
        # Run our unified document processor.
        #
        # It automatically identifies PDF or Excel files.
        extraction_result = process_document(file_path)

        # Record the successful completion time.
        completed_at = datetime.now(
            timezone.utc
        ).isoformat()

        # STEP 4:
        # Save the latest successful extraction.
        #
        # IMPORTANT:
        # We only update processing_results after successful
        # extraction. A failed attempt cannot overwrite
        # previously saved successful extraction data.
        save_processing_result(
            document_id=document_id,
            extraction_data=extraction_result,
            status="completed",
            started_at=started_at,
            completed_at=completed_at,
            error_message=None,
        )

        # STEP 5:
        # Mark this individual attempt as successful.
        complete_processing_attempt(
            attempt_id=attempt_id,
            status="completed",
        )

        # Update the document's overall status.
        update_document_status(
            document_id,
            "completed",
        )

        return {
            "document_id": document_id,
            "attempt_id": attempt_id,
            "attempt_number": attempt["attempt_number"],
            "status": "completed",
            "extraction": extraction_result,
        }

    except DocumentProcessingError as exc:

        # Record when the failed attempt finished.
        completed_at = datetime.now(
            timezone.utc
        ).isoformat()

        # STEP 6:
        # Record a standardized error category.
        #
        # The detailed error message is preserved separately
        # for debugging and troubleshooting.
        error_code = "DOCUMENT_PROCESSING_FAILED"

        error_message = str(exc)

        # Update the individual attempt.
        complete_processing_attempt(
            attempt_id=attempt_id,
            status="failed",
            error_code=error_code,
            error_message=error_message,
        )

        # Update the document's current status.
        update_document_status(
            document_id,
            "failed",
        )

        # IMPORTANT:
        # We deliberately DO NOT call save_processing_result()
        # here. The previous successful extraction remains intact.

        # Pass the original error to the API layer.
        raise

# ==============================================================================
# 1. Service Exception Handler (align with `except DocumentProcessingError:`)
# ==============================================================================
    except Exception:
        # Handle unexpected application errors.
        # These are different from known document extraction errors
        # and should be recorded separately.
        completed_at = datetime.now(timezone.utc).isoformat()

        # Record a generic internal processing failure.
        # Avoid exposing internal exception details here.
        complete_processing_attempt(
            attempt_id=attempt_id,
            status="failed",
            error_code="INTERNAL_PROCESSING_ERROR",
            error_message="An unexpected processing error occurred.",
        )

        # Mark the document as failed.
        update_document_status(
            document_id,
            "failed",
        )

        # Re-raise the original exception so the API can handle it appropriately.
        raise


# ==============================================================================
# 2. documents.py Endpoint Error Handling
# ==============================================================================
    try:
        processing_result = process_and_save_document(
            document_id=document_id,
            file_path=file_path,
        )

    except DocumentProcessingError as exc:
        # Known document-processing failures.
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        # Unexpected application failures.
        # Keep internal exception details out of the HTTP response.
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred during document processing",
        ) from exc


# ==============================================================================
# 3. tests/test_processing_history.py
# ==============================================================================
from app.db.database import initialize_database
from app.services.document_repository import create_document_record
from app.services.processing_repository import (
    complete_processing_attempt,
    get_processing_history,
    get_processing_result,
    save_processing_result,
    start_processing_attempt,
)


def create_test_document():
    """Create a document record for processing history tests."""
    return create_document_record(
        original_filename="invoice.pdf",
        stored_filename="invoice.pdf",
        content_type="application/pdf",
        file_size=1024,
    )


def test_multiple_processing_attempts(tmp_path, monkeypatch):
    # Isolate this test from the real application database.
    monkeypatch.setattr(
        "app.db.database.settings.database_path",
        tmp_path / "document_ai.db",
    )

    initialize_database()
    document = create_test_document()

    # Create the first processing attempt.
    first_attempt = start_processing_attempt(document.id)
    complete_processing_attempt(
        attempt_id=first_attempt["attempt_id"],
        status="completed",
    )

    # Create a second processing attempt.
    second_attempt = start_processing_attempt(document.id)
    complete_processing_attempt(
        attempt_id=second_attempt["attempt_id"],
        status="failed",
        error_code="DOCUMENT_PROCESSING_FAILED",
        error_message="Invalid document contents",
    )

    # Retrieve the complete processing history.
    history = get_processing_history(document.id)

    # Both attempts should be present, with newest attempts appearing first.
    assert len(history) == 2
    assert history[0]["attempt_number"] == 2
    assert history[1]["attempt_number"] == 1
    assert history[0]["status"] == "failed"
    assert history[1]["status"] == "completed"


def test_failed_attempt_does_not_replace_successful_result(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.db.database.settings.database_path",
        tmp_path / "document_ai.db",
    )

    initialize_database()
    document = create_test_document()

    # Define an example of a successful extraction.
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

    # Simulate another processing attempt.
    failed_attempt = start_processing_attempt(document.id)
    complete_processing_attempt(
        attempt_id=failed_attempt["attempt_id"],
        status="failed",
        error_code="DOCUMENT_PROCESSING_FAILED",
        error_message="Extraction failed",
    )

    # Retrieve the previously successful result.
    saved_result = get_processing_result(document.id)

    # The original successful extraction must still exist.
    assert saved_result["status"] == "completed"
    assert saved_result["extracted_data"] == successful_extraction

    # The failed attempt should exist separately in history.
    history = get_processing_history(document.id)
    assert len(history) == 1
    assert history[0]["status"] == "failed"


def test_processing_attempt_numbers_increment(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.db.database.settings.database_path",
        tmp_path / "document_ai.db",
    )

    initialize_database()
    document = create_test_document()

    first = start_processing_attempt(document.id)
    second = start_processing_attempt(document.id)
    third = start_processing_attempt(document.id)

    assert first["attempt_number"] == 1
    assert second["attempt_number"] == 2
    assert third["attempt_number"] == 3


def test_processing_history_for_unknown_document(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.db.database.settings.database_path",
        tmp_path / "document_ai.db",
    )

    initialize_database()
    history = get_processing_history("unknown-document")

    assert history == []
