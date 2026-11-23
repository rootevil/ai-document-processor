
from fastapi import APIRouter, File, UploadFile

from app.core.config import settings
from app.services.document_validator import validate_document


router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    await validate_document(
        file=file,
        max_size=settings.max_upload_size,
    )

    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "message": "Document validated successfully",
    }
