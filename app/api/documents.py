
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from app.services.document_processing_service import (
    process_and_save_document,
)
from app.core.config import settings
from app.schemas.document import DocumentRecord
from app.schemas.invoice import InvoiceFieldReviewRequest
from app.services.document_repository import (
    create_document_record,
    get_document_record,
    list_document_records,
)

from app.document_processing.document_processor import (
    process_document,
    DocumentProcessingError,
)

from app.services.document_storage import save_document
from app.services.document_validator import validate_document

from app.services.processing_repository import (
    get_processing_result,
    get_processing_history,
    get_processing_attempt_result,
    record_invoice_field_review,
    get_invoice_field_reviews,
    get_latest_invoice_field_reviews,
    DocumentAlreadyProcessingError,
    DocumentLifecycleError,
)

router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


@router.post(
    "/upload",
    response_model=DocumentRecord,
    summary="Upload Document",
)
async def upload_document(file: UploadFile = File(...)):
    await validate_document(
        file=file,
        max_size=settings.max_upload_size,
    )

    stored_filename, file_size = await save_document(
        file=file,
        upload_dir=settings.upload_dir,
    )

    document = create_document_record(
        original_filename=file.filename,
        stored_filename=stored_filename,
        content_type=file.content_type,
        file_size=file_size,
    )

    return document


@router.get(
    "/",
    response_model=list[DocumentRecord],
    summary="List Documents",
)
def get_documents():
    documents = list_document_records()

    return documents


@router.get(
    "/{document_id}",
    response_model=DocumentRecord,
    summary="Retrieve Document",
)
def get_document(document_id: str):
    document = get_document_record(document_id)

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    return document


@router.get(
    "/{document_id}/download",
    summary="Download Document",
)
def download_document(document_id: str):
    # Step 1: Retrieve document metadata.
    document = get_document_record(document_id)

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    # Step 2: Construct the storage path.
    stored_filename = document.stored_filename

    # Reject unexpected path components.
    if stored_filename != Path(stored_filename).name:
        raise HTTPException(
            status_code=404,
            detail="Document file not found",
        )

    upload_dir = settings.upload_dir.resolve()
    file_path = (upload_dir / stored_filename).resolve()

    # Ensure the resolved path remains inside upload_dir.
    if file_path.parent != upload_dir:
        raise HTTPException(
            status_code=404,
            detail="Document file not found",
        )

    # Step 3: Check whether the file exists.
    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Document file not found",
        )

    # Step 4: Return the original document.
    return FileResponse(
        path=file_path,
        filename=document.original_filename,
        media_type=document.content_type,
    )


@router.post("/{document_id}/process")
def process_uploaded_document(document_id: str):
    """
    Process an uploaded document and persist its results.

    Unlike the previous implementation, this endpoint
    now saves extraction results in SQLite.
    """

    # STEP 1:
    # Find the uploaded document using its database ID.
    document = get_document_record(document_id)

    # Return HTTP 404 if the document doesn't exist.
    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    # STEP 2:
    # Resolve the upload directory.
    upload_dir = settings.upload_dir.resolve()

    # Use the unique stored filename rather than the
    # original filename supplied by the user.
    stored_filename = document.stored_filename

    # Prevent unexpected path components.
    if stored_filename != Path(stored_filename).name:
        raise HTTPException(
            status_code=404,
            detail="Document file not found",
        )

    # Construct the absolute path of the stored document.
    file_path = (upload_dir / stored_filename).resolve()

    # Ensure the file remains inside the upload directory.
    if file_path.parent != upload_dir:
        raise HTTPException(
            status_code=404,
            detail="Document file not found",
        )

    # STEP 3:
    # Verify the physical file exists and still matches the
    # size recorded when it was uploaded.
    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Document file not found",
        )

    try:
        stored_file_size = file_path.stat().st_size
    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail="Unable to verify the stored document",
        ) from exc

    if stored_file_size != document.file_size:
        raise HTTPException(
            status_code=409,
            detail="Stored document size does not match its recorded metadata",
        )

    # STEP 4:
    # Call the processing service.
    #
    # The service handles extraction, status updates
    # and persistence of the extracted information.
    try:

        processing_result = process_and_save_document(
            document_id=document_id,
            file_path=file_path,
        )

    except DocumentAlreadyProcessingError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    except DocumentLifecycleError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc
    
    except DocumentProcessingError as exc:

        # The service has already saved the failed status
        # and error message in SQLite.
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    # STEP 5:
    # Return the result after successful persistence.
    return {
        "document_id": document.id,
        "original_filename": document.original_filename,
        "status": processing_result["status"],
        "extraction": processing_result["extraction"],
    }


@router.get("/{document_id}/result")
def retrieve_processing_result(document_id: str):
    """
    Retrieve previously saved extraction results.

    This endpoint does not process the document again.
    It reads the existing processing result from SQLite.
    """

    # STEP 1:
    # Confirm that the document exists.
    document = get_document_record(document_id)

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    # STEP 2:
    # Retrieve the saved processing result.
    result = get_processing_result(document_id)

    # The document exists, but it hasn't been processed yet.
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="No processing result found for this document",
        )

    # STEP 3:
    # Return the saved result.
    #
    # We don't call the extraction engine here.
    # This endpoint only reads from SQLite.
    return {
        "document_id": document.id,
        "original_filename": document.original_filename,
        "status": result["status"],
        "extraction": result["extracted_data"],
        "error_message": result["error_message"],
        "started_at": result["started_at"],
        "completed_at": result["completed_at"],
    }


@router.get("/{document_id}/history")
def retrieve_processing_history(document_id: str):
    """
    Retrieve the complete processing history of a document.

    This endpoint returns every processing attempt,
    including successful and failed attempts.

    It does not execute document extraction.
    """

    # STEP 1:
    # Verify that the requested document exists.
    document = get_document_record(document_id)

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    # STEP 2:
    # Retrieve all historical processing attempts.
    history = get_processing_history(document_id)

    # STEP 3:
    # Return the historical records.
    return {
        "document_id": document.id,
        "original_filename": document.original_filename,
        "total_attempts": len(history),
        "attempts": history,
    }


# =============================================================
# INVOICE FIELD REVIEW API
# =============================================================

def _get_reviewable_attempt(
    document_id: str,
    attempt_id: str,
):
    """
    Verify that a document exists and that the requested attempt
    belongs to it and has an extraction snapshot.

    This prevents accessing one document's extraction through
    another document's URL.
    """

    document = get_document_record(document_id)

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    attempts = get_processing_history(document_id)

    matching_attempt = next(
        (
            attempt
            for attempt in attempts
            if attempt["attempt_id"] == attempt_id
        ),
        None,
    )

    if matching_attempt is None:
        raise HTTPException(
            status_code=404,
            detail="Processing attempt not found for this document",
        )

    snapshot = get_processing_attempt_result(attempt_id)

    if snapshot is None:
        raise HTTPException(
            status_code=404,
            detail="No extraction snapshot found for this attempt",
        )

    return document, snapshot


@router.get(
    "/{document_id}/attempts/{attempt_id}/extraction",
    summary="Retrieve Original Attempt Extraction",
)
def retrieve_attempt_extraction(
    document_id: str,
    attempt_id: str,
):
    """Retrieve the immutable extraction snapshot for an attempt."""

    _, snapshot = _get_reviewable_attempt(
        document_id,
        attempt_id,
    )

    return snapshot


@router.post(
    "/{document_id}/attempts/{attempt_id}/reviews",
    status_code=201,
    summary="Submit Invoice Field Review",
)
def submit_invoice_field_review(
    document_id: str,
    attempt_id: str,
    review: InvoiceFieldReviewRequest,
):
    """
    Record an approval, correction, or rejection for one invoice field.

    Human decisions are stored separately from the original extraction.
    """

    _get_reviewable_attempt(
        document_id,
        attempt_id,
    )

    try:
        review_id = record_invoice_field_review(
            attempt_id=attempt_id,
            field_name=review.field_name,
            decision=review.decision,
            corrected_value=review.corrected_value,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    # Retrieve the exact event that was just inserted.
    saved_review = next(
        item
        for item in get_invoice_field_reviews(attempt_id)
        if item["review_id"] == review_id
    )

    return {
        "attempt_id": attempt_id,
        **saved_review,
    }


@router.get(
    "/{document_id}/attempts/{attempt_id}/reviews",
    summary="Retrieve Invoice Field Review History",
)
def retrieve_invoice_field_review_history(
    document_id: str,
    attempt_id: str,
):
    """Retrieve every human review event for an extraction attempt."""

    _get_reviewable_attempt(
        document_id,
        attempt_id,
    )

    reviews = get_invoice_field_reviews(attempt_id)

    return {
        "document_id": document_id,
        "attempt_id": attempt_id,
        "total_reviews": len(reviews),
        "reviews": reviews,
    }


@router.get(
    "/{document_id}/attempts/{attempt_id}/reviews/latest",
    summary="Retrieve Latest Invoice Field Reviews",
)
def retrieve_latest_invoice_field_reviews(
    document_id: str,
    attempt_id: str,
):
    """Retrieve the most recent decision independently for each field."""

    _get_reviewable_attempt(
        document_id,
        attempt_id,
    )

    latest_reviews = get_latest_invoice_field_reviews(attempt_id)

    return {
        "document_id": document_id,
        "attempt_id": attempt_id,
        "total_fields_reviewed": len(latest_reviews),
        "reviews": latest_reviews,
    }
