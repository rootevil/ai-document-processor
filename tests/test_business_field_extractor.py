
"""
Tests for business-field extraction.

These tests verify:
1. PDF invoice field extraction.
2. Excel invoice field extraction.
3. Source-reference preservation.
4. Missing-field handling.
5. Formula-cell protection.
6. Document classification.
7. Input validation.
"""

import pytest

from tests.create_sample_pdf import create_sample_pdf
from tests.create_sample_excel import create_sample_excel

from app.document_processing.document_processor import (
    process_document,
)

from app.document_processing.business_field_extractor import (
    extract_invoice_fields,
    BusinessFieldExtractionError,
)
from app.document_processing.value_normalizer import (
    normalize_business_fields,
)


def test_extract_invoice_fields_from_pdf(tmp_path):
    """Extract invoice fields from PDF page text."""

    pdf_path = tmp_path / "sample_invoice.pdf"

    create_sample_pdf(pdf_path)

    extraction_result = process_document(pdf_path)

    result = extract_invoice_fields(extraction_result)

    assert result["document_type"] == "invoice"

    fields = result["fields"]

    assert fields["invoice_number"]["value"] == "INV-1001"

    assert fields["invoice_date"]["value"] == "2026-11-24"

    assert fields["subtotal"]["value"] == "1000"

    assert fields["total_amount"]["value"] == "1150"

    # Verify that the invoice number points to page 1.
    assert fields["invoice_number"]["references"][0] == {
        "type": "page",
        "page_number": 1,
    }

    # Verify that the total points to page 2.
    assert fields["total_amount"]["references"][0] == {
        "type": "page",
        "page_number": 2,
    }


def test_extract_invoice_fields_from_excel(tmp_path):
    """Extract invoice fields from Excel worksheets."""

    excel_path = tmp_path / "sample_invoice.xlsx"

    create_sample_excel(excel_path)

    extraction_result = process_document(excel_path)

    result = extract_invoice_fields(extraction_result)

    assert result["document_type"] == "invoice"

    fields = result["fields"]

    assert fields["invoice_number"]["value"] == "INV-1001"

    assert fields["invoice_date"]["value"] == "2026-11-24"

    assert fields["customer_name"]["value"] == "ABC Technologies"

    # Verify the original Excel value cell is preserved.
    assert fields["invoice_number"]["references"][0] == {
        "type": "cell",
        "worksheet_name": "Invoice",
        "cell_reference": "B2",
    }

    # Customer information comes from another worksheet.
    assert fields["customer_name"]["references"][0] == {
        "type": "cell",
        "worksheet_name": "Customer Details",
        "cell_reference": "B1",
    }


def test_missing_invoice_fields_return_none(tmp_path):
    """Missing fields must not be guessed or fabricated."""

    pdf_path = tmp_path / "sample_invoice.pdf"

    create_sample_pdf(pdf_path)

    extraction_result = process_document(pdf_path)

    result = extract_invoice_fields(extraction_result)

    fields = result["fields"]

    assert fields["vendor_name"]["value"] is None

    assert fields["due_date"]["value"] is None

    assert fields["tax_amount"]["value"] is None

    assert fields["currency"]["value"] is None


def test_extract_fields_from_multiline_receipt_pdf():
    """Recognize values on the line after their PDF labels."""

    extraction_result = {
        "source_filename": "vercel_receipt.pdf",
        "file_type": "pdf",
        "sections": [
            {
                "section_type": "page",
                "section_name": "1",
                "content": {
                    "text": (
                        "Receipt\n"
                        "Invoice number\n"
                        "GS0VG4VQ-0001\n"
                        "Date paid\n"
                        "August 24, 2026\n"
                        "Vercel Inc.\n"
                        "Bill to\n"
                        "rootevil's projects\n"
                        "Subtotal\n"
                        "$11.25\n"
                        "Total\n"
                        "$11.25\n"
                        "Credited total\n"
                        "-$11.25\n"
                        "Adjusted invoice total\n"
                        "$0.00"
                    )
                },
                "references": [
                    {"type": "page", "page_number": 1}
                ],
            }
        ],
    }

    result = extract_invoice_fields(extraction_result)
    fields = result["fields"]

    assert fields["invoice_number"]["value"] == "GS0VG4VQ-0001"
    assert fields["vendor_name"]["value"] == "Vercel Inc."
    assert fields["customer_name"]["value"] == "rootevil's projects"
    assert fields["subtotal"]["value"] == "$11.25"
    assert fields["total_amount"]["value"] == "$11.25"
    assert fields["currency"]["value"] == "$"
    # A payment date is not necessarily the invoice issue date.
    assert fields["invoice_date"]["value"] is None
    # The credited/adjusted total must not replace the invoice total.
    assert fields["total_amount"]["value"] != "$0.00"
    assert fields["invoice_number"]["references"] == [
        {"type": "page", "page_number": 1}
    ]

    normalized = normalize_business_fields(result)
    assert normalized["fields"]["currency"]["normalization_status"] == "needs_review"


def test_currency_code_next_to_amount_is_extracted():
    extraction_result = {
        "source_filename": "usd_invoice.pdf",
        "file_type": "pdf",
        "sections": [
            {
                "section_type": "page",
                "section_name": "1",
                "content": {"text": "Invoice number: INV-200\nTotal: USD 25.00"},
                "references": [{"type": "page", "page_number": 1}],
            }
        ],
    }

    result = extract_invoice_fields(extraction_result)

    assert result["fields"]["total_amount"]["value"] == "USD 25.00"
    assert result["fields"]["currency"]["value"] == "USD"


def test_all_supported_invoice_fields_are_returned(tmp_path):
    """Every supported field must exist in the result."""

    pdf_path = tmp_path / "sample_invoice.pdf"

    create_sample_pdf(pdf_path)

    extraction_result = process_document(pdf_path)

    result = extract_invoice_fields(extraction_result)

    expected_fields = {
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

    assert set(result["fields"].keys()) == expected_fields

    for field in result["fields"].values():

        assert "value" in field

        assert "references" in field

        assert isinstance(field["references"], list)


def test_excel_formula_is_not_used_as_invoice_amount():
    """Uncalculated formulas must not be treated as amounts."""

    extraction_result = {
        "source_filename": "formula_invoice.xlsx",
        "file_type": "xlsx",
        "sections": [
            {
                "section_type": "worksheet",
                "section_name": "Invoice",
                "content": {
                    "rows": [
                        {
                            "row_number": 1,
                            "cells": [
                                {
                                    "cell_reference": "A1",
                                    "row_number": 1,
                                    "column_number": 1,
                                    "value": "Total",
                                    "data_type": "s",
                                },
                                {
                                    "cell_reference": "B1",
                                    "row_number": 1,
                                    "column_number": 2,
                                    "value": "=SUM(B2:B3)",
                                    "data_type": "f",
                                },
                            ],
                        }
                    ]
                },
                "references": [],
            }
        ],
    }

    result = extract_invoice_fields(extraction_result)

    assert result["document_type"] == "invoice"

    assert result["fields"]["total_amount"]["value"] is None


def test_non_invoice_document_is_classified_as_unknown():
    """Documents without invoice indicators are not classified as invoices."""

    extraction_result = {
        "source_filename": "annual_report.pdf",
        "file_type": "pdf",
        "sections": [
            {
                "section_type": "page",
                "section_name": "1",
                "content": {
                    "text": "Annual financial report"
                },
                "references": [
                    {
                        "type": "page",
                        "page_number": 1,
                    }
                ],
            }
        ],
    }

    result = extract_invoice_fields(extraction_result)

    assert result["document_type"] == "unknown"

    assert result["fields"]["invoice_number"]["value"] is None


def test_unsupported_file_type_is_rejected():
    """Invoice extraction only supports PDF and XLSX."""

    extraction_result = {
        "source_filename": "invoice.csv",
        "file_type": "csv",
        "sections": [],
    }

    with pytest.raises(BusinessFieldExtractionError):

        extract_invoice_fields(extraction_result)


def test_invalid_extraction_result_is_rejected():
    """Invalid input structures must produce a clear error."""

    with pytest.raises(BusinessFieldExtractionError):

        extract_invoice_fields(None)
