
from fastapi.testclient import TestClient

from app.db.database import initialize_database
from app.main import app

from tests.create_sample_pdf import create_sample_pdf


client = TestClient(app)


def test_process_pdf_and_retrieve_saved_result(
    tmp_path,
    monkeypatch,
):
    # Isolate the test database and upload directory.
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

    # Create a real PDF for this integration test.
    pdf_path = tmp_path / "sample_invoice.pdf"

    create_sample_pdf(pdf_path)

    # Upload the PDF using the existing upload endpoint.
    upload_response = client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                "sample_invoice.pdf",
                pdf_path.read_bytes(),
                "application/pdf",
            )
        },
    )

    assert upload_response.status_code == 200

    document_id = upload_response.json()["id"]

    # Process the uploaded document.
    process_response = client.post(
        f"/api/v1/documents/{document_id}/process"
    )

    assert process_response.status_code == 200

    process_result = process_response.json()

    assert process_result["status"] == "completed"

    # Retrieve the result using the new GET endpoint.
    retrieve_response = client.get(
        f"/api/v1/documents/{document_id}/result"
    )

    assert retrieve_response.status_code == 200

    saved_result = retrieve_response.json()

    assert saved_result["document_id"] == document_id

    assert saved_result["status"] == "completed"

    assert (
        saved_result["extraction"]
        == process_result["extraction"]
    )

    # Verify that the extracted invoice number
    # survived the database storage and retrieval cycle.
    first_page = saved_result["extraction"]["sections"][0]

    assert "INV-1001" in first_page["content"]["text"]


def test_retrieve_result_before_processing(
    tmp_path,
    monkeypatch,
):
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

    # Create and upload a PDF without processing it.
    pdf_path = tmp_path / "sample_invoice.pdf"

    create_sample_pdf(pdf_path)

    upload_response = client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                "sample_invoice.pdf",
                pdf_path.read_bytes(),
                "application/pdf",
            )
        },
    )

    document_id = upload_response.json()["id"]

    # Request a result that doesn't exist yet.
    response = client.get(
        f"/api/v1/documents/{document_id}/result"
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "No processing result found for this document"
    }

def test_invoice_contract_survives_database_persistence(
    tmp_path,
    monkeypatch,
):
    """The invoice contract must survive JSON storage and retrieval."""

    from app.core.config import settings

    monkeypatch.setattr(
        settings,
        "ai_extraction_enabled",
        False,
    )

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

    pdf_path = tmp_path / "sample_invoice.pdf"
    create_sample_pdf(pdf_path)

    upload_response = client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                "sample_invoice.pdf",
                pdf_path.read_bytes(),
                "application/pdf",
            )
        },
    )

    assert upload_response.status_code == 200

    document_id = upload_response.json()["id"]

    process_response = client.post(
        f"/api/v1/documents/{document_id}/process"
    )

    assert process_response.status_code == 200

    original_extraction = process_response.json()["extraction"]

    assert "invoice_extraction" in original_extraction

    retrieve_response = client.get(
        f"/api/v1/documents/{document_id}/result"
    )

    assert retrieve_response.status_code == 200

    retrieved_extraction = retrieve_response.json()["extraction"]

    # The complete extraction must remain identical after persistence.
    assert retrieved_extraction == original_extraction

    # Verify that the shared contract survived serialization.
    invoice = retrieved_extraction["invoice_extraction"]

    assert (
        invoice["fields"]["invoice_number"]["value"]
        == "INV-1001"
    )

    assert (
        invoice["fields"]["invoice_number"]["references"][0]
        ["page_number"]
        == 1
    )