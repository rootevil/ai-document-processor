
import pymupdf
import pytest
from pathlib import Path
from tests.create_sample_pdf import create_sample_pdf

from app.document_processing.pdf_extractor import (
    extract_pdf_text,
    PDFExtractionError,
)


def test_extract_pdf_text(tmp_path):

    pdf_path = tmp_path / "sample_invoice.pdf"

    create_sample_pdf(pdf_path)

    extracted_pages = extract_pdf_text(pdf_path)

    assert len(extracted_pages) == 2

    assert extracted_pages[0]["page_number"] == 1

    assert "INV-1001" in extracted_pages[0]["text"]

    assert extracted_pages[1]["page_number"] == 2

    assert "Subtotal: 1000" in extracted_pages[1]["text"]


def test_extract_missing_pdf():

    missing_path = Path("missing_invoice.pdf")

    with pytest.raises(PDFExtractionError):
        extract_pdf_text(missing_path)


def test_extract_invalid_pdf(tmp_path):

    pdf_path = tmp_path / "invalid.pdf"

    pdf_path.write_bytes(b"This is not a valid PDF")

    with pytest.raises(PDFExtractionError):
        extract_pdf_text(pdf_path)
