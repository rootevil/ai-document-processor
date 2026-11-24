
from pathlib import Path

import pytest

from tests.create_sample_pdf import create_sample_pdf
from tests.create_sample_excel import create_sample_excel

from app.document_processing.document_processor import (
    process_document,
    DocumentProcessingError,
)


def test_process_pdf_document(tmp_path):

    pdf_path = tmp_path / "sample_invoice.pdf"

    create_sample_pdf(pdf_path)

    result = process_document(pdf_path)

    assert result["source_filename"] == "sample_invoice.pdf"

    assert result["file_type"] == "pdf"

    assert len(result["sections"]) == 2

    first_page = result["sections"][0]

    assert first_page["section_type"] == "page"

    assert first_page["section_name"] == "1"

    assert first_page["references"][0]["page_number"] == 1

    assert "INV-1001" in first_page["content"]["text"]


def test_process_excel_document(tmp_path):

    excel_path = tmp_path / "sample_invoice.xlsx"

    create_sample_excel(excel_path)

    result = process_document(excel_path)

    assert result["source_filename"] == "sample_invoice.xlsx"

    assert result["file_type"] == "xlsx"

    assert len(result["sections"]) == 2

    first_sheet = result["sections"][0]

    assert first_sheet["section_type"] == "worksheet"

    assert first_sheet["section_name"] == "Invoice"

    references = first_sheet["references"]

    invoice_number_reference = next(
        reference
        for reference in references
        if reference["cell_reference"] == "B2"
    )

    assert invoice_number_reference["row_number"] == 2

    assert invoice_number_reference["column_number"] == 2


def test_process_unsupported_document(tmp_path):

    file_path = tmp_path / "invoice.csv"

    file_path.write_text(
        "Invoice Number,INV-1001"
    )

    with pytest.raises(DocumentProcessingError):

        process_document(file_path)


def test_process_missing_document():

    file_path = Path("missing_document.pdf")

    with pytest.raises(DocumentProcessingError):

        process_document(file_path)


def test_process_invalid_pdf(tmp_path):

    pdf_path = tmp_path / "invalid.pdf"

    pdf_path.write_bytes(
        b"This is not a valid PDF"
    )

    with pytest.raises(DocumentProcessingError):

        process_document(pdf_path)
