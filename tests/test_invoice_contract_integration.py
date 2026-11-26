"""
Integration tests for the invoice contract adapter.

These tests use real sample PDF and Excel documents and pass their
actual processor output into the shared InvoiceExtraction contract.

The production document-processing pipeline is not modified here.
"""

from copy import deepcopy

import pytest

from app.core.config import settings
from app.document_processing.document_processor import process_document
from app.document_processing.invoice_contract_adapter import (
    build_invoice_extraction,
)
from app.schemas.invoice import ExtractionSource

from tests.create_sample_pdf import create_sample_pdf
from tests.create_sample_excel import create_sample_excel


@pytest.fixture
def disable_ai_extraction(monkeypatch):
    """Keep integration tests independent of an external AI provider."""
    monkeypatch.setattr(
        settings,
        "ai_extraction_enabled",
        False,
    )


def test_real_pdf_processor_output_converts_to_invoice_contract(
    tmp_path,
    disable_ai_extraction,
):
    """Verify that real PDF extraction output maps into the shared contract."""

    # Create and process the same kind of PDF used by existing processor tests.
    pdf_path = tmp_path / "sample_invoice.pdf"
    create_sample_pdf(pdf_path)

    processor_result = process_document(pdf_path)

    # Confirm that this is actual PDF processor output.
    assert processor_result["file_type"] == "pdf"
    assert processor_result["business_fields"]["document_type"] == "invoice"

    # Convert the processor result without changing the processor itself.
    invoice = build_invoice_extraction(processor_result)

    assert invoice.document_type == "invoice"

    # Verify extracted and normalized invoice values.
    assert invoice.fields.invoice_number.value == "INV-1001"
    assert invoice.fields.invoice_date.value == "2026-11-24"

    assert (
        invoice.fields.total_amount.normalized_value
        == "1150"
    )

    # Verify that the original PDF page reference survives conversion.
    invoice_number_references = (
        invoice.fields.invoice_number.references
    )

    assert len(invoice_number_references) >= 1
    assert invoice_number_references[0].type == "page"
    assert invoice_number_references[0].page_number == 1

    # The current processor does not produce evidence text or confidence.
    # The adapter must not invent either value.
    assert invoice.fields.invoice_number.evidence == []
    assert invoice.fields.invoice_number.confidence is None

    # Confirm that the extraction source is correctly identified.
    assert (
        invoice.fields.invoice_number.source
        == ExtractionSource.RULE_BASED
    )


def test_real_excel_processor_output_converts_to_invoice_contract(
    tmp_path,
    disable_ai_extraction,
):
    """Verify that real Excel extraction output retains cell provenance."""

    # Generate and process a real sample workbook.
    excel_path = tmp_path / "sample_invoice.xlsx"
    create_sample_excel(excel_path)

    processor_result = process_document(excel_path)

    # Confirm that the processor identified the Excel document.
    assert processor_result["file_type"] == "xlsx"
    assert processor_result["business_fields"]["document_type"] == "invoice"

    # Convert the processor result into the shared invoice contract.
    invoice = build_invoice_extraction(processor_result)

    assert invoice.document_type == "invoice"

    # Verify a value extracted from the Customer Details worksheet.
    customer_name = invoice.fields.customer_name

    assert customer_name.value == "ABC Technologies"
    assert customer_name.normalized_value == "ABC Technologies"

    # The exact worksheet and cell reference must remain available.
    assert len(customer_name.references) >= 1

    customer_reference = customer_name.references[0]

    assert customer_reference.type == "cell"
    assert customer_reference.sheet_name == "Customer Details"
    assert customer_reference.cell_reference == "B1"

    # The current business-field extractor supplies the worksheet name
    # and cell address, but does not include separate row/column numbers.
    # The adapter must preserve the available reference without inventing
    # additional coordinates.
    assert customer_reference.row_number is None
    assert customer_reference.column_number is None

    # No evidence text or confidence should be fabricated.
    assert customer_name.evidence == []
    assert customer_name.confidence is None


def test_real_processor_result_is_not_mutated_by_adapter(
    tmp_path,
    disable_ai_extraction,
):
    """Ensure contract conversion does not alter the original processor data."""

    pdf_path = tmp_path / "sample_invoice.pdf"
    create_sample_pdf(pdf_path)

    processor_result = process_document(pdf_path)

    # Keep a snapshot of the complete processor result.
    original_result = deepcopy(processor_result)

    # Build the contract.
    build_invoice_extraction(processor_result)

    # The adapter must behave as a conversion layer, not modify its input.
    assert processor_result == original_result


def test_real_ai_disabled_processor_result_rejects_ai_selection(
    tmp_path,
    disable_ai_extraction,
):
    """Ensure disabled AI output cannot be mistaken for completed extraction."""

    pdf_path = tmp_path / "sample_invoice.pdf"
    create_sample_pdf(pdf_path)

    processor_result = process_document(pdf_path)

    assert processor_result["ai_extraction"]["status"] == "disabled"

    # The AI adapter selection must reject an AI result that does not exist.
    from app.document_processing.invoice_contract_adapter import (
        ExtractionSelection,
        InvoiceContractAdapterError,
    )

    with pytest.raises(InvoiceContractAdapterError):
        build_invoice_extraction(
            processor_result,
            source=ExtractionSelection.AI,
        )
