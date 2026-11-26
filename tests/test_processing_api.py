
from fastapi.testclient import TestClient

from app.db.database import initialize_database
from app.main import app
from app.services.processing_repository import start_processing_attempt
from app.services.processing_repository import update_document_status
from tests.create_sample_pdf import create_sample_pdf
from tests.create_sample_excel import create_sample_excel


# Create a test client that allows us to send HTTP requests
# to our FastAPI application without starting a real server.
client = TestClient(app)


def test_process_uploaded_pdf(tmp_path, monkeypatch):

    # Use temporary directories so our tests don't modify
    # the application's actual upload directory or database.
    upload_dir = tmp_path / "uploads"

    monkeypatch.setattr(
        "app.api.documents.settings.upload_dir",
        upload_dir,
    )

    monkeypatch.setattr(
        "app.api.documents.settings.database_path",
        tmp_path / "document_ai.db",
    )

    # Initialize a fresh SQLite database for this test.
    initialize_database()

    # Generate a real two-page PDF using our test utility.
    pdf_path = tmp_path / "sample_invoice.pdf"

    create_sample_pdf(pdf_path)

    # Read the PDF bytes so we can upload it through the API.
    pdf_content = pdf_path.read_bytes()

    upload_response = client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                "sample_invoice.pdf",
                pdf_content,
                "application/pdf",
            )
        },
    )

    # Confirm that the upload succeeded.
    assert upload_response.status_code == 200

    # Retrieve the unique document ID returned by the API.
    document_id = upload_response.json()["id"]

    # Request extraction using the document ID.
    process_response = client.post(
        f"/api/v1/documents/{document_id}/process"
    )

    assert process_response.status_code == 200

    result = process_response.json()

    # Verify that the response identifies the uploaded document.
    assert result["document_id"] == document_id

    assert result["original_filename"] == "sample_invoice.pdf"

    # Verify that PDF extraction was performed.
    extraction = result["extraction"]

    assert extraction["file_type"] == "pdf"

    assert len(extraction["sections"]) == 2

    # Verify that the invoice number was extracted.
    first_page = extraction["sections"][0]

    assert "INV-1001" in first_page["content"]["text"]


def test_process_uploaded_excel(tmp_path, monkeypatch):

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

    # Generate a real Excel workbook.
    excel_path = tmp_path / "sample_invoice.xlsx"

    create_sample_excel(excel_path)

    excel_content = excel_path.read_bytes()

    upload_response = client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                "sample_invoice.xlsx",
                excel_content,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert upload_response.status_code == 200

    document_id = upload_response.json()["id"]

    # Request Excel extraction through the same API endpoint.
    process_response = client.post(
        f"/api/v1/documents/{document_id}/process"
    )

    assert process_response.status_code == 200

    result = process_response.json()

    extraction = result["extraction"]

    # Confirm that the unified processor identified Excel.
    assert extraction["file_type"] == "xlsx"

    # Confirm that both worksheets were extracted.
    assert len(extraction["sections"]) == 2

    first_sheet = extraction["sections"][0]

    assert first_sheet["section_name"] == "Invoice"

    # Confirm that the invoice number is present in the
    # extracted worksheet content.
    extracted_cells = [
        cell
        for row in first_sheet["content"]["rows"]
        for cell in row["cells"]
    ]

    invoice_number = next(
        cell
        for cell in extracted_cells
        if cell["cell_reference"] == "B2"
    )

    assert invoice_number["value"] == "INV-1001"


def test_process_nonexistent_document(tmp_path, monkeypatch):

    monkeypatch.setattr(
        "app.api.documents.settings.database_path",
        tmp_path / "document_ai.db",
    )

    initialize_database()

    # Request processing for an ID that does not exist.
    response = client.post(
        "/api/v1/documents/nonexistent-id/process"
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Document not found"
    }


def test_process_missing_physical_file(tmp_path, monkeypatch):

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

    # Create and upload a genuine PDF.
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

    document = upload_response.json()

    document_id = document["id"]

    stored_filename = document["stored_filename"]

    # Simulate someone deleting the physical file while
    # leaving its database record untouched.
    (upload_dir / stored_filename).unlink()

    response = client.post(
        f"/api/v1/documents/{document_id}/process"
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Document file not found"
    }

def test_process_already_processing_document_returns_conflict(
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

    # Simulate another request already processing this document.
    start_processing_attempt(document_id)

    response = client.post(
        f"/api/v1/documents/{document_id}/process"
    )

    assert response.status_code == 409
    assert "already being processed" in response.json()["detail"]


def test_process_document_with_invalid_lifecycle_state_returns_conflict(
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

    update_document_status(document_id, "archived")

    response = client.post(
        f"/api/v1/documents/{document_id}/process"
    )

    assert response.status_code == 409
    assert "cannot be processed" in response.json()["detail"]


def test_process_document_with_changed_file_size_returns_conflict(
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

    document = upload_response.json()
    stored_path = upload_dir / document["stored_filename"]

    # Change the stored file after upload to simulate corruption.
    stored_path.write_bytes(stored_path.read_bytes() + b"corruption")

    response = client.post(
        f"/api/v1/documents/{document['id']}/process"
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Stored document size does not match its recorded metadata"
    }

def test_process_uploaded_pdf_returns_invoice_contract(
    tmp_path,
    monkeypatch,
):
    """The processing API should expose the shared invoice contract."""

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
        "app.api.documents.settings.database_path",
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

    extraction = process_response.json()["extraction"]

    # Existing processor output must remain available.
    assert extraction["business_fields"]["document_type"] == "invoice"
    assert extraction["normalized_business_fields"] is not None

    # The new shared contract must also be available.
    assert "invoice_extraction" in extraction

    invoice = extraction["invoice_extraction"]

    assert invoice["document_type"] == "invoice"

    assert (
        invoice["fields"]["invoice_number"]["value"]
        == "INV-1001"
    )

    assert (
        invoice["fields"]["invoice_number"]["source"]
        == "rule_based"
    )

    assert (
        invoice["fields"]["invoice_number"]["references"][0]
        ["page_number"]
        == 1
    )