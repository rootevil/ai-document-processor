
from datetime import datetime, timezone
from uuid import uuid4

from app.db.database import get_connection
from app.schemas.document import DocumentRecord


def create_document_record(
    original_filename: str,
    stored_filename: str,
    content_type: str,
    file_size: int,
) -> DocumentRecord:

    document = DocumentRecord(
        id=str(uuid4()),
        original_filename=original_filename,
        stored_filename=stored_filename,
        content_type=content_type,
        file_size=file_size,
        status="uploaded",
        uploaded_at=datetime.now(timezone.utc),
    )

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO documents (
                id,
                original_filename,
                stored_filename,
                content_type,
                file_size,
                status,
                uploaded_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document.id,
                document.original_filename,
                document.stored_filename,
                document.content_type,
                document.file_size,
                document.status,
                document.uploaded_at.isoformat(),
            ),
        )

    return document


def list_document_records() -> list[DocumentRecord]:

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM documents
            ORDER BY uploaded_at DESC
            """
        ).fetchall()

    return [
        DocumentRecord(
            **{
                **dict(row),
                "uploaded_at": datetime.fromisoformat(
                    row["uploaded_at"]
                ),
            }
        )
        for row in rows
    ]


def get_document_record(
    document_id: str,
) -> DocumentRecord | None:

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM documents
            WHERE id = ?
            """,
            (document_id,),
        ).fetchone()

    if row is None:
        return None

    return DocumentRecord(
        **{
            **dict(row),
            "uploaded_at": datetime.fromisoformat(
                row["uploaded_at"]
            ),
        }
    )
