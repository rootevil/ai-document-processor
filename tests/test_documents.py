
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_upload_document(tmp_path, monkeypatch):
    file_content = b"%PDF-1.7\nSample invoice content"

    monkeypatch.setattr(
        "app.api.documents.settings.upload_dir",
        tmp_path,
    )

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

    assert data["original_filename"] == "invoice.pdf"
    assert data["content_type"] == "application/pdf"
    assert data["file_size"] == len(file_content)

    assert data["message"] == (
        "Document uploaded and stored successfully"
    )

    stored_filename = data["stored_filename"]

    assert stored_filename.endswith(".pdf")
    assert stored_filename != "invoice.pdf"

    saved_file = tmp_path / stored_filename

    assert saved_file.exists()
    assert saved_file.read_bytes() == file_content


    assert response.status_code == 200

    # assert response.json() == {
    #     "filename": "invoice.pdf",
    #     "content_type": "application/pdf",
    #     "message": "Document validated successfully",
    # }


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



def test_duplicate_filenames_create_separate_files(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        "app.api.documents.settings.upload_dir",
        tmp_path,
    )

    first_response = client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                "invoice.pdf",
                b"%PDF-1.7\nFirst invoice",
                "application/pdf",
            )
        },
    )

    second_response = client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                "invoice.pdf",
                b"%PDF-1.7\nSecond invoice",
                "application/pdf",
            )
        },
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    first_filename = first_response.json()["stored_filename"]
    second_filename = second_response.json()["stored_filename"]

    assert first_filename != second_filename

    assert (tmp_path / first_filename).read_bytes() == (
        b"%PDF-1.7\nFirst invoice"
    )

    assert (tmp_path / second_filename).read_bytes() == (
        b"%PDF-1.7\nSecond invoice"
    )
