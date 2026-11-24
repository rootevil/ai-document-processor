
from fastapi import APIRouter, File, UploadFile

from app.core.config import settings
from app.schemas.document import DocumentRecord
from app.services.document_repository import (
    create_document_record,
    list_document_records,
)
from app.services.document_storage import save_document
from app.services.document_validator import validate_document


router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


@router.post("/upload", response_model=DocumentRecord)
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


@router.get("/", response_model=list[DocumentRecord])
def get_documents():

    documents = list_document_records()

    return documents
