
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.core.config import settings
from app.schemas.document import DocumentRecord
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
    Process an uploaded document and return its extracted content.

    This endpoint:
    1. Finds the document metadata in SQLite.
    2. Locates the original file in upload storage.
    3. Sends the file to the unified document processor.
    4. Returns the extracted content as JSON.
    """

    # STEP 1:
    # Find the document record using its unique database ID.
    #
    # We reuse the repository function created in Chunk 12.
    document = get_document_record(document_id)

    # If no matching record exists, return HTTP 404.
    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    # STEP 2:
    # Get the stored filename from the database.
    #
    # We use the stored filename, not the original filename,
    # because our storage system saves files using unique names.
    stored_filename = document.stored_filename

    # STEP 3:
    # Resolve the upload directory to its absolute filesystem path.
    upload_dir = settings.upload_dir.resolve()

    # Reject unexpected path components.
    # This prevents a database filename from escaping the
    # configured upload directory.
    if stored_filename != Path(stored_filename).name:
        raise HTTPException(
            status_code=404,
            detail="Document file not found",
        )

    # Construct the physical file path.
    file_path = (upload_dir / stored_filename).resolve()

    # Confirm that the resolved file remains directly inside
    # the configured upload directory.
    if file_path.parent != upload_dir:
        raise HTTPException(
            status_code=404,
            detail="Document file not found",
        )

    # STEP 4:
    # Confirm that the physical file actually exists.
    #
    # A database record can exist even if someone has manually
    # deleted the corresponding file from storage.
    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Document file not found",
        )

    # STEP 5:
    # Call our unified document processing service.
    #
    # We don't need to check whether this is a PDF or Excel file
    # here. The document processor handles format detection.
    try:
        extraction_result = process_document(file_path)

    except DocumentProcessingError as exc:

        # The file exists, but its contents cannot be processed.
        # HTTP 422 indicates that the supplied document could not
        # be processed successfully.
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    # STEP 6:
    # Return the extraction result along with the database ID.
    #
    # The ID lets the client identify which uploaded document
    # produced these extraction results.
    return {
        "document_id": document.id,
        "original_filename": document.original_filename,
        "extraction": extraction_result,
    }
