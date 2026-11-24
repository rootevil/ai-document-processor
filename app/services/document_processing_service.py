
from datetime import datetime, timezone
from pathlib import Path

from app.document_processing.document_processor import (
    process_document,
    DocumentProcessingError,
)

from app.services.processing_repository import (
    update_document_status,
    save_processing_result,
)


def process_and_save_document(
    document_id: str,
    file_path: Path,
) -> dict:
    """
    Coordinate document extraction and database persistence.

    Responsibilities:
    1. Mark the document as processing.
    2. Extract the document contents.
    3. Save successful extraction results.
    4. Save failure information if extraction fails.
    5. Update the document's final status.
    """

    # Record when processing begins.
    started_at = datetime.now(
        timezone.utc
    ).isoformat()

    # STEP 1:
    # Tell the database that document processing has started.
    update_document_status(
        document_id,
        "processing",
    )

    # Save an initial processing record.
    #
    # This allows us to identify documents that entered
    # processing even if extraction hasn't completed yet.
    save_processing_result(
        document_id=document_id,
        extraction_data=None,
        status="processing",
        started_at=started_at,
    )

    try:

        # STEP 2:
        # Call our unified processor.
        #
        # The processor automatically chooses PDF or Excel
        # extraction based on the file extension.
        extraction_result = process_document(file_path)

        # Record when successful processing finished.
        completed_at = datetime.now(
            timezone.utc
        ).isoformat()

        # STEP 3:
        # Save the extracted information permanently.
        save_processing_result(
            document_id=document_id,
            extraction_data=extraction_result,
            status="completed",
            started_at=started_at,
            completed_at=completed_at,
        )

        # STEP 4:
        # Update the original document's status.
        update_document_status(
            document_id,
            "completed",
        )

        # Return the persisted extraction data to the API.
        return {
            "document_id": document_id,
            "status": "completed",
            "extraction": extraction_result,
        }

    except DocumentProcessingError as exc:

        # Extraction failed, but we want to preserve
        # the failure information for future troubleshooting.
        completed_at = datetime.now(
            timezone.utc
        ).isoformat()

        # Save the error message instead of extraction data.
        save_processing_result(
            document_id=document_id,
            extraction_data=None,
            status="failed",
            started_at=started_at,
            completed_at=completed_at,
            error_message=str(exc),
        )

        # Update the original document status.
        update_document_status(
            document_id,
            "failed",
        )

        # Re-raise the error so the API can return
        # an appropriate HTTP response.
        raise
