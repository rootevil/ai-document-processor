
from pathlib import Path

import pytest

from tests.create_sample_excel import create_sample_excel

from app.document_processing.excel_extractor import (
    extract_excel_data,
    ExcelExtractionError,
)


def test_extract_excel_data(tmp_path):

    excel_path = tmp_path / "sample_invoice.xlsx"

    create_sample_excel(excel_path)

    extracted_sheets = extract_excel_data(excel_path)

    assert len(extracted_sheets) == 2

    invoice_sheet = extracted_sheets[0]

    assert invoice_sheet["worksheet_name"] == "Invoice"

    customer_sheet = extracted_sheets[1]

    assert customer_sheet["worksheet_name"] == "Customer Details"


def test_extract_cell_references(tmp_path):

    excel_path = tmp_path / "sample_invoice.xlsx"

    create_sample_excel(excel_path)

    extracted_sheets = extract_excel_data(excel_path)

    invoice_sheet = extracted_sheets[0]

    extracted_cells = [
        cell
        for row in invoice_sheet["rows"]
        for cell in row["cells"]
    ]

    invoice_number = next(
        cell
        for cell in extracted_cells
        if cell["cell_reference"] == "B2"
    )

    assert invoice_number["value"] == "INV-1001"

    assert invoice_number["row_number"] == 2

    assert invoice_number["column_number"] == 2


def test_extract_excel_formula(tmp_path):

    excel_path = tmp_path / "sample_invoice.xlsx"

    create_sample_excel(excel_path)

    extracted_sheets = extract_excel_data(excel_path)

    invoice_sheet = extracted_sheets[0]

    extracted_cells = [
        cell
        for row in invoice_sheet["rows"]
        for cell in row["cells"]
    ]

    formula_cell = next(
        cell
        for cell in extracted_cells
        if cell["cell_reference"] == "D8"
    )

    assert formula_cell["value"] == "=SUM(B6:B7)"

    assert formula_cell["data_type"] == "f"


def test_extract_merged_cells(tmp_path):

    excel_path = tmp_path / "sample_invoice.xlsx"

    create_sample_excel(excel_path)

    extracted_sheets = extract_excel_data(excel_path)

    invoice_sheet = extracted_sheets[0]

    assert "A1:C1" in invoice_sheet["merged_cells"]


def test_extract_missing_excel():

    missing_path = Path("missing_invoice.xlsx")

    with pytest.raises(ExcelExtractionError):
        extract_excel_data(missing_path)


def test_extract_invalid_excel(tmp_path):

    excel_path = tmp_path / "invalid.xlsx"

    excel_path.write_bytes(
        b"This is not a valid Excel workbook"
    )

    with pytest.raises(ExcelExtractionError):
        extract_excel_data(excel_path)


def test_reject_unsupported_excel_extension(tmp_path):

    excel_path = tmp_path / "invoice.xls"

    excel_path.write_bytes(b"sample")

    with pytest.raises(ExcelExtractionError):
        extract_excel_data(excel_path)
