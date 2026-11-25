
from fastapi.testclient import TestClient

from app.db.database import initialize_database
from app.main import app

from tests.create_sample_pdf import create_sample_pdf

from app.services.processing_repository import (
    start_processing_attempt,
    complete_processing_attempt,
)


client = TestClient(app)


def test_retrieve_processing_history(
    tmp_path,
    monkeypatch,
):
    # Isolate the database and uploaded files.
    upload_dir = tmp_path / "uploads"

    monkeypatch.setattr(
        "app.api.documents.settings.upload_dir",
        upload_dir,
    )

    monkeypatch.setattr(
        "app.db.database.settings.database_path",
        tmp_path / "document_ai.db",
    )

    initialize_database()

    # Generate a sample PDF.
    pdf_path = tmp_path / "invoice.pdf"

    create_sample_pdf(pdf_path)

    # Upload the document through the existing API.
    upload_response = client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                "invoice.pdf",
                pdf_path.read_bytes(),
                "application/pdf",
            )
        },
    )

    assert upload_response.status_code == 200

    document_id = upload_response.json()["id"]

    # Create a successful attempt.
    first = start_processing_attempt(document_id)

    complete_processing_attempt(
        attempt_id=first["attempt_id"],
        status="completed",
    )

    # Create a failed attempt.
    second = start_processing_attempt(document_id)

    complete_processing_attempt(
        attempt_id=second["attempt_id"],
        status="failed",
        error_code="DOCUMENT_PROCESSING_FAILED",
        error_message="Sample extraction failure",
    )

    # Request processing history through the API.
    response = client.get(
        f"/api/v1/documents/{document_id}/history"
    )

    assert response.status_code == 200

    result = response.json()

    assert result["document_id"] == document_id

    assert result["total_attempts"] == 2

    assert result["attempts"][0]["attempt_number"] == 2

    assert result["attempts"][0]["status"] == "failed"

    assert result["attempts"][1]["attempt_number"] == 1

    assert result["attempts"][1]["status"] == "completed"


def test_history_for_nonexistent_document(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        "app.db.database.settings.database_path",
        tmp_path / "document_ai.db",
    )

    initialize_database()

    response = client.get(
        "/api/v1/documents/unknown-document/history"
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Document not found"
    }
