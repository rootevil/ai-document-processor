
import json

from datetime import datetime, timezone

from app.db.database import get_connection


def update_document_status(
    document_id: str,
    status: str,
) -> None:
    """
    Update the latest status of an uploaded document.

    This function updates the status column in the
    existing documents table.

    Example statuses:
    - uploaded
    - processing
    - completed
    - failed
    """

    # Open a database connection using our existing
    # database connection manager.
    with get_connection() as connection:

        # Update only the document matching the supplied ID.
        connection.execute(
            """
            UPDATE documents
            SET status = ?
            WHERE id = ?
            """,
            (status, document_id),
        )


def save_processing_result(
    document_id: str,
    extraction_data: dict | None,
    status: str,
    started_at: str,
    completed_at: str | None = None,
    error_message: str | None = None,
) -> None:
    """
    Save or update the latest processing result.

    Extraction data is converted into JSON before being
    stored in SQLite.

    If a result already exists for this document,
    it is replaced with the latest processing result.
    """

    # Convert the Python dictionary into a JSON string.
    #
    # SQLite stores this JSON as TEXT. We convert it back
    # into a Python dictionary when retrieving the result.
    extracted_json = (
        json.dumps(extraction_data)
        if extraction_data is not None
        else None
    )

    # Open a database connection.
    with get_connection() as connection:

        # INSERT creates the first processing result.
        #
        # ON CONFLICT updates the existing result when
        # the same document is processed again.
        connection.execute(
            """
            INSERT INTO processing_results (
                document_id,
                status,
                extracted_data,
                error_message,
                started_at,
                completed_at
            )
            VALUES (?, ?, ?, ?, ?, ?)

            ON CONFLICT(document_id)
            DO UPDATE SET
                status = excluded.status,
                extracted_data = excluded.extracted_data,
                error_message = excluded.error_message,
                started_at = excluded.started_at,
                completed_at = excluded.completed_at
            """,
            (
                document_id,
                status,
                extracted_json,
                error_message,
                started_at,
                completed_at,
            ),
        )


def get_processing_result(document_id: str) -> dict | None:
    """
    Retrieve the latest processing result for a document.

    Returns None if the document has not been processed.
    """

    # Retrieve the processing result from SQLite.
    with get_connection() as connection:

        row = connection.execute(
            """
            SELECT *
            FROM processing_results
            WHERE document_id = ?
            """,
            (document_id,),
        ).fetchone()

    # No processing result exists for this document.
    if row is None:
        return None

    # Convert the database row into a normal Python dictionary.
    result = dict(row)

    # Convert the stored JSON string back into a Python object.
    if result["extracted_data"] is not None:
        result["extracted_data"] = json.loads(
            result["extracted_data"]
        )

    return result
