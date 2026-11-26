
"""
Database connection and initialization module.

Responsibilities:
1. Create and manage SQLite database connections.
2. Ensure database directories exist.
3. Enable foreign-key constraints.
4. Create the application database tables.
5. Create indexes for efficient database queries.
"""

import sqlite3

from contextlib import contextmanager
from typing import Iterator

from app.core.config import settings


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """
    Provide a managed SQLite database connection.

    This context manager:
    - Creates the database directory if it does not exist.
    - Opens a SQLite connection.
    - Returns rows as dictionary-like objects.
    - Enables foreign-key constraints.
    - Commits successful transactions.
    - Rolls back failed transactions.
    - Closes the connection after use.
    """

    # Read the database file path from application settings.
    database_path = settings.database_path

    # Create the parent directory if it does not already exist.
    database_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    #
    # If another request is currently writing to SQLite, this connection waits up to 10 seconds before raising a database locking error.
    connection = sqlite3.connect(
        database_path,
        timeout=10.0,
    )

    # Return rows as dictionary-like objects.
    connection.row_factory = sqlite3.Row

    # Enforce foreign-key constraints declared in our tables.
    connection.execute("PRAGMA foreign_keys = ON")

    # Wait up to 10 seconds if another connection holds a database lock.
    connection.execute("PRAGMA busy_timeout = 10000")

    try:
        # Manage the transaction automatically.
        # Successful operations are committed.
        # Failed operations are rolled back.
        with connection:
            yield connection

    finally:
        # Always close the database connection,
        # even if an exception occurs.
        connection.close()


def initialize_database() -> None:
    """
    Initialize the application database.

    Creates the following tables if they do not already exist:

    1. documents:
       Stores uploaded document metadata.

    2. processing_results:
       Stores the latest successful extraction result
       for each document.

    3. processing_attempts:
       Stores the complete history of processing attempts,
       including successful and failed attempts.
    """

    # Open a managed database connection.
    with get_connection() as connection:

        # executescript() executes multiple SQL statements.
        # All table and index definitions are kept inside
        # this single SQL script.
        connection.executescript(
            """
            -- =====================================================
            -- TABLE 1: documents
            -- =====================================================
            -- Stores metadata about uploaded documents.
            --
            -- Each document receives a unique ID.
            -- The stored filename is unique to prevent collisions.
            -- The status tracks the document's processing lifecycle.

            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                original_filename TEXT NOT NULL,
                stored_filename TEXT NOT NULL UNIQUE,
                content_type TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                status TEXT NOT NULL,
                uploaded_at TEXT NOT NULL
            );


            -- =====================================================
            -- TABLE 2: processing_results
            -- =====================================================
            -- Stores the latest successful processing result.
            --
            -- document_id links this record to the documents table.
            -- extracted_data stores extraction output as JSON text.
            -- error_message stores any associated error information.
            -- started_at and completed_at track processing timestamps.

            CREATE TABLE IF NOT EXISTS processing_results (
                document_id TEXT PRIMARY KEY,

                status TEXT NOT NULL,

                extracted_data TEXT,

                error_message TEXT,

                started_at TEXT NOT NULL,

                completed_at TEXT,

                FOREIGN KEY (document_id)
                    REFERENCES documents(id)
                    ON DELETE CASCADE
            );


            -- =====================================================
            -- TABLE 3: processing_attempts
            -- =====================================================
            -- Stores every processing attempt for a document.
            --
            -- A document can have multiple processing attempts.
            -- Each attempt receives a unique attempt ID.
            -- attempt_number tracks the sequence of attempts.
            -- Failed attempts are preserved for troubleshooting.
            --
            -- UNIQUE(document_id, attempt_number) ensures that
            -- the same document cannot have duplicate attempt numbers.

            CREATE TABLE IF NOT EXISTS processing_attempts (
                attempt_id TEXT PRIMARY KEY,

                document_id TEXT NOT NULL,

                attempt_number INTEGER NOT NULL,

                status TEXT NOT NULL,

                error_code TEXT,

                error_message TEXT,

                started_at TEXT NOT NULL,

                completed_at TEXT,

                FOREIGN KEY (document_id)
                    REFERENCES documents(id)
                    ON DELETE CASCADE,

                UNIQUE (document_id, attempt_number)
            );


            -- =====================================================
            -- INDEX: processing_attempts
            -- =====================================================
            -- Improves retrieval performance when searching
            -- processing attempts belonging to a document.

            CREATE INDEX IF NOT EXISTS idx_processing_attempts_document_id
            ON processing_attempts(document_id);

            -- =====================================================
            -- INDEX: ONE ACTIVE PROCESSING ATTEMPT PER DOCUMENT
            -- =====================================================
            -- Allow only one active processing attempt per document.
            -- Completed and failed attempts remain in the history.

            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_one_active_processing_attempt_per_document
            ON processing_attempts(document_id)
            WHERE status = 'processing';   



            -- =====================================================
            -- TABLE: processing_attempt_results
            -- Immutable extraction snapshot for each attempt.
            -- =====================================================

            CREATE TABLE IF NOT EXISTS processing_attempt_results (
                attempt_id TEXT PRIMARY KEY,
                extracted_data TEXT NOT NULL,
                created_at TEXT NOT NULL,

                FOREIGN KEY (attempt_id)
                    REFERENCES processing_attempts(attempt_id)
                    ON DELETE CASCADE
            );

            -- Prevent accidental changes to an extraction snapshot.
            CREATE TRIGGER IF NOT EXISTS
            prevent_processing_attempt_result_update
            BEFORE UPDATE ON processing_attempt_results
            BEGIN
                SELECT RAISE(ABORT, 'processing attempt results are immutable');
            END;


            -- =====================================================
            -- TABLE: invoice_field_reviews
            -- Append-only history of individual field decisions.
            -- =====================================================

            CREATE TABLE IF NOT EXISTS invoice_field_reviews (
                review_sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                review_id TEXT NOT NULL UNIQUE,
                attempt_id TEXT NOT NULL,

                field_name TEXT NOT NULL CHECK (field_name IN (
                    'invoice_number',
                    'invoice_date',
                    'due_date',
                    'vendor_name',
                    'customer_name',
                    'subtotal',
                    'tax_amount',
                    'total_amount',
                    'currency'
                )),

                decision TEXT NOT NULL CHECK (
                    decision IN ('approved', 'corrected', 'rejected')
                ),

                corrected_value TEXT,
                reviewer_id TEXT,
                reviewed_at TEXT NOT NULL,

                CHECK (
                    (decision = 'corrected' AND corrected_value IS NOT NULL)
                    OR
                    (decision IN ('approved', 'rejected') AND corrected_value IS NULL)
                ),

                FOREIGN KEY (attempt_id)
                    REFERENCES processing_attempt_results(attempt_id)
                    ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS
            idx_invoice_field_reviews_attempt_field_sequence
            ON invoice_field_reviews(
                attempt_id,
                field_name,
                review_sequence
            );

            -- Review events are historical records; do not update them.
            CREATE TRIGGER IF NOT EXISTS
            prevent_invoice_field_review_update
            BEFORE UPDATE ON invoice_field_reviews
            BEGIN
                SELECT RAISE(ABORT, 'invoice field reviews are append-only');
            END;

            -- Prevent deletion of original extraction snapshots.
            CREATE TRIGGER IF NOT EXISTS
            prevent_processing_attempt_result_delete
            BEFORE DELETE ON processing_attempt_results
            BEGIN
                SELECT RAISE(
                    ABORT,
                    'processing attempt results cannot be deleted'
                );
            END;

            -- Prevent deletion of human review history.
            CREATE TRIGGER IF NOT EXISTS
            prevent_invoice_field_review_delete
            BEFORE DELETE ON invoice_field_reviews
            BEGIN
                SELECT RAISE(
                    ABORT,
                    'invoice field reviews cannot be deleted'
                );
            END;
            """
        )
