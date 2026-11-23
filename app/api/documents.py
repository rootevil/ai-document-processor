
from fastapi import APIRouter, File, UploadFile

from app.core.config import settings
from app.services.document_storage import save_document
from app.services.document_validator import validate_document


router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):

    # Step 1: Validate the uploaded document.
    await validate_document(
        file=file,
        max_size=settings.max_upload_size,
    )

    # Step 2: Save the validated document.
    stored_filename, file_size = await save_document(
        file=file,
        upload_dir=settings.upload_dir,
    )

    # Step 3: Return upload information.
    return {
        "original_filename": file.filename,
        "stored_filename": stored_filename,
        "file_size": file_size,
        "content_type": file.content_type,
        "message": "Document uploaded and stored successfully",
    }
