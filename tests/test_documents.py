
import pytest

from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.database import initialize_database
from app.main import app
from app.services.document_repository import (
    create_document_record,
    list_document_records,
)


client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_environment(tmp_path, monkeypatch):
    """
    Give every test its own database and upload directory.

    This prevents tests from sharing database records
    or interfering with actual application files.
    """

    monkeypatch.setattr(
        settings,
        "database_path",
        tmp_path / "document_ai.db",
    )

    monkeypatch.setattr(
        settings,
        "upload_dir",
        tmp_path / "uploads",
    )

    initialize_database()


# --------------------------------------------------
# 1. Successful document upload
# --------------------------------------------------

def test_upload_document(tmp_path):

    file_content = b"%PDF-1.7\nSample invoice content"

    response = client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                "invoice.pdf",
                file_content,
                "application/pdf",
            )
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"]
    assert data["original_filename"] == "invoice.pdf"
    assert data["content_type"] == "application/pdf"
    assert data["file_size"] == len(file_content)
    assert data["status"] == "uploaded"
    assert data["uploaded_at"]

    stored_filename = data["stored_filename"]

    assert stored_filename.endswith(".pdf")
    assert stored_filename != "invoice.pdf"

    saved_file = (
        tmp_path / "uploads" / stored_filename
    )

    assert saved_file.exists()
    assert saved_file.read_bytes() == file_content


# --------------------------------------------------
# 2. Reject unsupported file formats
# --------------------------------------------------

def test_reject_unsupported_file():

    response = client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                "invoice.docx",
                b"Sample document",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 415


# --------------------------------------------------
# 3. Reject invalid PDF signatures
# --------------------------------------------------

def test_reject_invalid_pdf_signature():

    response = client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                "invoice.pdf",
                b"This is not a PDF",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 400


# --------------------------------------------------
# 4. Reject empty files
# --------------------------------------------------

def test_reject_empty_file():

    response = client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                "invoice.pdf",
                b"",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 400


# --------------------------------------------------
# 5. Reject oversized files
# --------------------------------------------------

def test_reject_oversized_file():

    file_content = b"%PDF-" + (
        b"A" * (10 * 1024 * 1024)
    )

    response = client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                "large_invoice.pdf",
                file_content,
                "application/pdf",
            )
        },
    )

    assert response.status_code == 413


# --------------------------------------------------
# 6. Duplicate filenames create separate files
# --------------------------------------------------

def test_duplicate_filenames_create_separate_files(
    tmp_path,
):

    first_content = b"%PDF-1.7\nFirst invoice"
    second_content = b"%PDF-1.7\nSecond invoice"

    first_response = client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                "invoice.pdf",
                first_content,
                "application/pdf",
            )
        },
    )

    second_response = client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                "invoice.pdf",
                second_content,
                "application/pdf",
            )
        },
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    first_data = first_response.json()
    second_data = second_response.json()

    first_filename = first_data["stored_filename"]
    second_filename = second_data["stored_filename"]

    assert first_filename != second_filename

    assert first_data["id"] != second_data["id"]

    first_file = (
        tmp_path / "uploads" / first_filename
    )

    second_file = (
        tmp_path / "uploads" / second_filename
    )

    assert first_file.exists()
    assert second_file.exists()

    assert first_file.read_bytes() == first_content
    assert second_file.read_bytes() == second_content


# --------------------------------------------------
# 7. List uploaded documents
# --------------------------------------------------

def test_list_documents():

    file_content = b"%PDF-1.7\nSample invoice"

    upload_response = client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                "invoice.pdf",
                file_content,
                "application/pdf",
            )
        },
    )

    assert upload_response.status_code == 200

    response = client.get(
        "/api/v1/documents/"
    )

    assert response.status_code == 200

    documents = response.json()

    assert len(documents) == 1

    document = documents[0]

    assert document["id"] == upload_response.json()["id"]
    assert document["original_filename"] == "invoice.pdf"
    assert document["status"] == "uploaded"
    assert document["file_size"] == len(file_content)
    assert document["stored_filename"].endswith(".pdf")
    assert document["uploaded_at"] is not None


# --------------------------------------------------
# 8. Document records persist across connections
# --------------------------------------------------

def test_document_records_persist():

    created = create_document_record(
        original_filename="invoice.pdf",
        stored_filename="unique-invoice.pdf",
        content_type="application/pdf",
        file_size=1024,
    )

    retrieved = list_document_records()

    assert len(retrieved) == 1

    assert retrieved[0].id == created.id

    assert (
        retrieved[0].original_filename
        == "invoice.pdf"
    )

    assert retrieved[0].file_size == 1024

    assert retrieved[0].status == "uploaded"

#RETRIEVE DOCUMENT METADATA
def test_get_document(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.api.documents.settings.upload_dir",
        tmp_path / "uploads",
    )

    monkeypatch.setattr(
        "app.api.documents.settings.database_path",
        tmp_path / "document_ai.db",
    )

    initialize_database()

    upload_response = client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                "invoice.pdf",
                b"%PDF-1.7\nSample invoice",
                "application/pdf",
            )
        },
    )

    document_id = upload_response.json()["id"]

    response = client.get(
        f"/api/v1/documents/{document_id}"
    )

    assert response.status_code == 200

    document = response.json()

    assert document["id"] == document_id
    assert document["original_filename"] == "invoice.pdf"
    assert document["status"] == "uploaded"

#DOWNLOAD THE ORIGINAL DATA
def test_download_document(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.api.documents.settings.upload_dir",
        tmp_path / "uploads",
    )

    monkeypatch.setattr(
        "app.api.documents.settings.database_path",
        tmp_path / "document_ai.db",
    )

    initialize_database()

    file_content = b"%PDF-1.7\nOriginal invoice content"

    upload_response = client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                "invoice.pdf",
                file_content,
                "application/pdf",
            )
        },
    )

    document_id = upload_response.json()["id"]

    response = client.get(
        f"/api/v1/documents/{document_id}/download"
    )

    assert response.status_code == 200

    assert response.content == file_content

    assert response.headers["content-type"] == "application/pdf"

    assert "invoice.pdf" in response.headers["content-disposition"]

#...HANDLE NON EXISTENT DOCUMENT

def test_get_nonexistent_document(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.api.documents.settings.database_path",
        tmp_path / "document_ai.db",
    )

    initialize_database()

    response = client.get(
        "/api/v1/documents/nonexistent-document-id"
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Document not found"
    }

#HANDLE MISSING PHYSICAL FILES

def test_download_missing_physical_file(
    tmp_path,
    monkeypatch,
):
    upload_dir = tmp_path / "uploads"

    monkeypatch.setattr(
        "app.api.documents.settings.upload_dir",
        upload_dir,
    )

    monkeypatch.setattr(
        "app.api.documents.settings.database_path",
        tmp_path / "document_ai.db",
    )

    initialize_database()

    upload_response = client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                "invoice.pdf",
                b"%PDF-1.7\nSample invoice",
                "application/pdf",
            )
        },
    )

    document_id = upload_response.json()["id"]
    stored_filename = upload_response.json()["stored_filename"]

    # Simulate a file being deleted from storage.
    (upload_dir / stored_filename).unlink()

    response = client.get(
        f"/api/v1/documents/{document_id}/download"
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Document file not found"
    }
