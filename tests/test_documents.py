
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_upload_document():
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

    assert response.json() == {
        "filename": "invoice.pdf",
        "content_type": "application/pdf",
        "message": "Document validated successfully",
    }


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


def test_reject_oversized_file():
    file_content = b"%PDF-" + (b"A" * (10 * 1024 * 1024))

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
