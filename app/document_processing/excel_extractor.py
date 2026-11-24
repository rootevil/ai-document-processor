
from pathlib import Path

import openpyxl


class ExcelExtractionError(Exception):
    """Raised when an Excel workbook cannot be processed."""


def extract_excel_data(file_path: Path) -> list[dict]:
    """
    Extract data from every worksheet in an Excel workbook.

    Preserves worksheet names, row numbers,
    column numbers, and cell references.
    """

    if not file_path.is_file():
        raise ExcelExtractionError(
            "Excel file not found"
        )

    if file_path.suffix.lower() != ".xlsx":
        raise ExcelExtractionError(
            "Only .xlsx files are supported"
        )

    workbook = None

    try:
        workbook = openpyxl.load_workbook(
            file_path,
            data_only=False,
            read_only=False,
        )

        extracted_sheets = []

        for worksheet in workbook.worksheets:

            extracted_rows = []

            for row in worksheet.iter_rows():

                extracted_cells = []

                for cell in row:

                    if cell.value is not None:

                        extracted_cells.append(
                            {
                                "cell_reference": cell.coordinate,
                                "row_number": cell.row,
                                "column_number": cell.column,
                                "value": cell.value,
                                "data_type": cell.data_type,
                            }
                        )

                if extracted_cells:

                    extracted_rows.append(
                        {
                            "row_number": row[0].row,
                            "cells": extracted_cells,
                        }
                    )

            extracted_sheets.append(
                {
                    "worksheet_name": worksheet.title,
                    "max_row": worksheet.max_row,
                    "max_column": worksheet.max_column,
                    "merged_cells": [
                        str(merged_range)
                        for merged_range in worksheet.merged_cells.ranges
                    ],
                    "rows": extracted_rows,
                }
            )

        return extracted_sheets

    except ExcelExtractionError:
        raise

    except Exception as exc:
        raise ExcelExtractionError(
            "Unable to extract data from Excel workbook"
        ) from exc

    finally:
        if workbook is not None:
            workbook.close()
