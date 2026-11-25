
import json
import uuid
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
            AND status = 'completed'
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


def start_processing_attempt(document_id: str) -> dict:
    """
    Create a new processing attempt.

    Every time a document is processed, we create a new
    attempt instead of overwriting its previous history.

    Returns the unique attempt ID and attempt number.
    """

    # Generate a unique ID for this processing attempt.
    attempt_id = str(uuid.uuid4())

    # Record when this processing attempt begins.
    started_at = datetime.now(
        timezone.utc
    ).isoformat()

    with get_connection() as connection:

        # Find the highest previous attempt number
        # belonging to this document.
        row = connection.execute(
            """
            SELECT MAX(attempt_number) AS last_attempt
            FROM processing_attempts
            WHERE document_id = ?
            """,
            (document_id,),
        ).fetchone()

        # The first attempt starts at number 1.
        # Otherwise, increment the previous attempt number.
        attempt_number = (
            (row["last_attempt"] or 0) + 1
        )

        # Create a new historical processing record.
        connection.execute(
            """
            INSERT INTO processing_attempts (
                attempt_id,
                document_id,
                attempt_number,
                status,
                error_code,
                error_message,
                started_at,
                completed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                attempt_id,
                document_id,
                attempt_number,
                "processing",
                None,
                None,
                started_at,
                None,
            ),
        )

    return {
        "attempt_id": attempt_id,
        "attempt_number": attempt_number,
        "started_at": started_at,
    }


def complete_processing_attempt(
    attempt_id: str,
    status: str,
    error_code: str | None = None,
    error_message: str | None = None,
) -> None:
    """
    Finish an existing processing attempt.

    This function records whether extraction succeeded
    or failed.

    Historical attempts are updated, not deleted.
    """

    # Record when this processing attempt finishes.
    completed_at = datetime.now(
        timezone.utc
    ).isoformat()

    with get_connection() as connection:

        # Update the existing attempt using its unique ID.
        connection.execute(
            """
            UPDATE processing_attempts
            SET
                status = ?,
                error_code = ?,
                error_message = ?,
                completed_at = ?
            WHERE attempt_id = ?
            """,
            (
                status,
                error_code,
                error_message,
                completed_at,
                attempt_id,
            ),
        )


def get_processing_history(document_id: str) -> list[dict]:
    """
    Retrieve all processing attempts for a document.

    Results are returned in reverse chronological order,
    with the newest attempt appearing first.
    """

    with get_connection() as connection:

        # Retrieve all attempts associated with the document.
        rows = connection.execute(
            """
            SELECT *
            FROM processing_attempts
            WHERE document_id = ?
            ORDER BY attempt_number DESC
            """,
            (document_id,),
        ).fetchall()

    # Convert database rows into normal Python dictionaries.
    return [
        dict(row)
        for row in rows
    ]
