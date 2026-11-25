
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
    Coordinate document extraction and database persistence.

    Each execution creates a separate processing attempt.

    Successful extraction results are saved permanently.
    Failed attempts are recorded without overwriting
    previously successful extraction results.
    """

    # STEP 1:
    # Create a new processing attempt.
    attempt = start_processing_attempt(document_id)

    attempt_id = attempt["attempt_id"]
    started_at = attempt["started_at"]

    # STEP 2:
    # Mark the document as currently processing.
    update_document_status(
        document_id,
        "processing",
    )

    try:
        # STEP 3:
        # Extract the contents of the document.
        extraction_result = process_document(file_path)

        completed_at = datetime.now(
            timezone.utc
        ).isoformat()

        # STEP 4:
        # Save the successful extraction result.
        save_processing_result(
            document_id=document_id,
            extraction_data=extraction_result,
            status="completed",
            started_at=started_at,
            completed_at=completed_at,
            error_message=None,
        )

        # STEP 5:
        # Mark the processing attempt as completed.
        complete_processing_attempt(
            attempt_id=attempt_id,
            status="completed",
        )

        # STEP 6:
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

        # Record a known document-processing failure.
        complete_processing_attempt(
            attempt_id=attempt_id,
            status="failed",
            error_code="DOCUMENT_PROCESSING_FAILED",
            error_message=str(exc),
        )

        update_document_status(
            document_id,
            "failed",
        )

        # Do not overwrite the previous successful result.
        raise

    except Exception:

        # Record an unexpected application failure.
        complete_processing_attempt(
            attempt_id=attempt_id,
            status="failed",
            error_code="INTERNAL_PROCESSING_ERROR",
            error_message="An unexpected processing error occurred.",
        )

        update_document_status(
            document_id,
            "failed",
        )

        # Let the API layer handle the unexpected exception.
        raise
