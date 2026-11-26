
import json
import uuid
from datetime import datetime, timezone

from app.db.database import get_connection

class DocumentAlreadyProcessingError(Exception):
    """
    Raised when a document already has an active processing attempt.

    This prevents duplicate extraction requests from processing
    the same document simultaneously.
    """


class DocumentLifecycleError(Exception):
    """Raised when a document cannot be processed from its current state."""

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
    Atomically create a new processing attempt.

    This function:
    1. Acquires a SQLite write lock.
    2. Checks whether processing is already active.
    3. Calculates the next attempt number.
    4. Creates a new processing attempt.
    5. Updates the document status.

    All database operations happen inside one transaction.

    This prevents simultaneous requests from creating
    multiple active attempts for the same document.
    """

    # Generate a unique ID for this processing attempt.
    attempt_id = str(uuid.uuid4())

    # Record when this processing attempt begins.
    started_at = datetime.now(
        timezone.utc
    ).isoformat()

    with get_connection() as connection:

        # Acquire the SQLite write lock immediately.
        #
        # Other write transactions must wait until this
        # transaction commits or rolls back.
        connection.execute("BEGIN IMMEDIATE")

        # Check whether this document already has an
        # active processing attempt.
        active_attempt = connection.execute(
            """
            SELECT attempt_id
            FROM processing_attempts
            WHERE document_id = ?
            AND status = 'processing'
            LIMIT 1
            """,
            (document_id,),
        ).fetchone()

        # Do not allow another active attempt.
        if active_attempt is not None:
            raise DocumentAlreadyProcessingError(
                f"Document '{document_id}' is already being processed."
            )

        # Verify that the document exists and read its lifecycle status.
        document = connection.execute(
            """
            SELECT id, status
            FROM documents
            WHERE id = ?
            """,
            (document_id,),
        ).fetchone()

        if document is None:
            raise ValueError(
                f"Document '{document_id}' does not exist."
            )

        # A new attempt is allowed after upload or after a previous
        # attempt finished. Other states indicate an invalid transition.
        allowed_statuses = {"uploaded", "completed", "failed"}
        if document["status"] not in allowed_statuses:
            raise DocumentLifecycleError(
                f"Document '{document_id}' cannot be processed from "
                f"status '{document['status']}'."
            )

        # Find the highest previous attempt number.
        row = connection.execute(
            """
            SELECT MAX(attempt_number) AS last_attempt
            FROM processing_attempts
            WHERE document_id = ?
            """,
            (document_id,),
        ).fetchone()

        # The first attempt starts at number 1.
        # Every subsequent attempt increments the number.
        attempt_number = (
            (row["last_attempt"] or 0) + 1
        )

        # Create the new processing attempt.
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

        # Update the document status in the same transaction.
        connection.execute(
            """
            UPDATE documents
            SET status = ?
            WHERE id = ?
            """,
            ("processing", document_id),
        )

    # The connection context manager commits the transaction
    # after all operations complete successfully.

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

    if status not in {"completed", "failed"}:
        raise ValueError(
            "A processing attempt can only finish as 'completed' or 'failed'."
        )

    # Record when this processing attempt finishes.
    completed_at = datetime.now(
        timezone.utc
    ).isoformat()

    with get_connection() as connection:

        # Find the related document so its status can be updated
        # in the same transaction as the attempt.
        attempt = connection.execute(
            """
            SELECT document_id
            FROM processing_attempts
            WHERE attempt_id = ?
            AND status = 'processing'
            """,
            (attempt_id,),
        ).fetchone()

        if attempt is None:
            raise ValueError(
                f"Active processing attempt '{attempt_id}' was not found."
            )

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

        # Keep the document and attempt lifecycle states in sync.
        connection.execute(
            """
            UPDATE documents
            SET status = ?
            WHERE id = ?
            """,
            (status, attempt["document_id"]),
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


# =============================================================
# INVOICE REVIEW REPOSITORY
# =============================================================

SUPPORTED_INVOICE_REVIEW_FIELDS = {
    "invoice_number",
    "invoice_date",
    "due_date",
    "vendor_name",
    "customer_name",
    "subtotal",
    "tax_amount",
    "total_amount",
    "currency",
}

SUPPORTED_REVIEW_DECISIONS = {
    "approved",
    "corrected",
    "rejected",
}


def save_processing_attempt_result(
    attempt_id: str,
    extraction_data: dict,
) -> None:
    """
    Save the extraction output for one specific processing attempt.

    A snapshot is inserted once and cannot be overwritten. This keeps
    the original machine extraction available even after human review.
    """

    if not isinstance(extraction_data, dict):
        raise ValueError("extraction_data must be a dictionary.")

    serialized_data = json.dumps(extraction_data, allow_nan=False)
    created_at = datetime.now(timezone.utc).isoformat()

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO processing_attempt_results (
                attempt_id,
                extracted_data,
                created_at
            )
            VALUES (?, ?, ?)
            """,
            (attempt_id, serialized_data, created_at),
        )


def get_processing_attempt_result(
    attempt_id: str,
) -> dict | None:
    """
    Retrieve the immutable extraction snapshot for one attempt.
    """

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT attempt_id, extracted_data, created_at
            FROM processing_attempt_results
            WHERE attempt_id = ?
            """,
            (attempt_id,),
        ).fetchone()

    if row is None:
        return None

    result = dict(row)
    result["extracted_data"] = json.loads(result["extracted_data"])

    return result


def record_invoice_field_review(
    attempt_id: str,
    field_name: str,
    decision: str,
    corrected_value=None,
    reviewer_id: str | None = None,
) -> str:
    """
    Record one human decision for one invoice field.

    Decisions:
    - approved: accept the extracted value.
    - corrected: store a replacement value separately.
    - rejected: reject the extracted value.

    Every call creates a new review event. Previous decisions remain
    in the review history.
    """

    if field_name not in SUPPORTED_INVOICE_REVIEW_FIELDS:
        raise ValueError(f"Unsupported invoice field: {field_name}")

    if decision not in SUPPORTED_REVIEW_DECISIONS:
        raise ValueError(f"Unsupported review decision: {decision}")

    if decision == "corrected" and corrected_value is None:
        raise ValueError("A corrected decision requires corrected_value.")

    if decision in {"approved", "rejected"} and corrected_value is not None:
        raise ValueError(
            f"A {decision} decision cannot include corrected_value."
        )

    serialized_value = None

    if decision == "corrected":
        if isinstance(corrected_value, bool) or not isinstance(
            corrected_value, (str, int, float)
        ):
            raise ValueError(
                "corrected_value must be a string or numeric scalar."
            )

        try:
            serialized_value = json.dumps(
                corrected_value,
                allow_nan=False,
            )
        except (TypeError, ValueError) as error:
            raise ValueError("corrected_value must be valid JSON data.") from error

    review_id = str(uuid.uuid4())
    reviewed_at = datetime.now(timezone.utc).isoformat()

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO invoice_field_reviews (
                review_id,
                attempt_id,
                field_name,
                decision,
                corrected_value,
                reviewer_id,
                reviewed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                review_id,
                attempt_id,
                field_name,
                decision,
                serialized_value,
                reviewer_id,
                reviewed_at,
            ),
        )

    return review_id


def _deserialize_invoice_review(row) -> dict:
    """Convert a review database row into a Python dictionary."""

    review = dict(row)

    if review["corrected_value"] is not None:
        review["corrected_value"] = json.loads(
            review["corrected_value"]
        )

    return review


def get_invoice_field_reviews(
    attempt_id: str,
) -> list[dict]:
    """
    Retrieve every review event for an attempt, oldest first.
    """

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM invoice_field_reviews
            WHERE attempt_id = ?
            ORDER BY review_sequence ASC
            """,
            (attempt_id,),
        ).fetchall()

    return [
        _deserialize_invoice_review(row)
        for row in rows
    ]


def get_latest_invoice_field_reviews(
    attempt_id: str,
) -> dict[str, dict]:
    """
    Return the latest review event for each field in an attempt.

    The complete review history remains available through
    get_invoice_field_reviews().
    """

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM invoice_field_reviews
            WHERE attempt_id = ?
            ORDER BY review_sequence DESC
            """,
            (attempt_id,),
        ).fetchall()

    latest_reviews = {}

    for row in rows:
        review = _deserialize_invoice_review(row)
        field_name = review["field_name"]

        # Rows are newest first, so the first event for each field
        # is that field's latest decision.
        if field_name not in latest_reviews:
            latest_reviews[field_name] = review

    return latest_reviews
