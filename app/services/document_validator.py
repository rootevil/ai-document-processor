
from io import BytesIO
from pathlib import PurePosixPath
from zipfile import BadZipFile, ZipFile

from fastapi import HTTPException, UploadFile


ALLOWED_EXTENSIONS = {
    ".pdf",
    ".xlsx",
    ".csv",
}

ALLOWED_CONTENT_TYPES = {
    ".pdf": {"application/pdf"},
    ".xlsx": {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/zip",
    },
    ".csv": {
        "text/csv",
        "application/csv",
        "application/vnd.ms-excel",
    },
}


async def validate_document(
    file: UploadFile,
    max_size: int,
) -> None:
    filename = file.filename

    if not filename or not filename.strip():
        raise HTTPException(
            status_code=400,
            detail="Filename is required.",
        )

    if (
        "/" in filename
        or "\\" in filename
        or PurePosixPath(filename).name != filename
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid filename.",
        )

    extension = PurePosixPath(filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail="Unsupported file format. Allowed formats: PDF, XLSX, CSV.",
        )

    if file.content_type not in ALLOWED_CONTENT_TYPES[extension]:
        raise HTTPException(
            status_code=415,
            detail="File content type does not match an allowed format.",
        )

    content = await file.read(max_size + 1)

    await file.seek(0)

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty.",
        )

    if len(content) > max_size:
        raise HTTPException(
            status_code=413,
            detail="File exceeds the maximum allowed size.",
        )

    if extension == ".pdf":
        if not content.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=400,
                detail="Invalid PDF file signature.",
            )

    elif extension == ".xlsx":
        try:
            with ZipFile(BytesIO(content)) as archive:
                required_files = {
                    "[Content_Types].xml",
                    "xl/workbook.xml",
                }

                if not required_files.issubset(archive.namelist()):
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid XLSX file structure.",
                    )

        except BadZipFile:
            raise HTTPException(
                status_code=400,
                detail="Invalid XLSX archive.",
            )

    elif extension == ".csv":
        try:
            decoded_content = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=400,
                detail="CSV file must use UTF-8 encoding.",
            )

        if "\x00" in decoded_content:
            raise HTTPException(
                status_code=400,
                detail="Invalid CSV content.",
            )
