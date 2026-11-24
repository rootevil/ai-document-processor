
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
