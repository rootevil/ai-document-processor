
from pathlib import Path

from app.document_processing.pdf_extractor import (
    extract_pdf_text,
    PDFExtractionError,
)

from app.document_processing.excel_extractor import (
    extract_excel_data,
    ExcelExtractionError,
)


class DocumentProcessingError(Exception):
    """Raised when document processing fails."""


def process_document(file_path: Path) -> dict:
    """
    Process a supported document and return
    a unified extraction result.

    Supported formats:
    - PDF
    - XLSX
    """

    if not file_path.is_file():
        raise DocumentProcessingError(
            "Document file not found"
        )

    extension = file_path.suffix.lower()

    try:

        if extension == ".pdf":

            extracted_pages = extract_pdf_text(file_path)

            sections = []

            for page in extracted_pages:

                sections.append(
                    {
                        "section_type": "page",
                        "section_name": str(
                            page["page_number"]
                        ),
                        "content": {
                            "text": page["text"]
                        },
                        "references": [
                            {
                                "type": "page",
                                "page_number": page["page_number"],
                            }
                        ],
                    }
                )

            return {
                "source_filename": file_path.name,
                "file_type": "pdf",
                "sections": sections,
            }

        elif extension == ".xlsx":

            extracted_sheets = extract_excel_data(file_path)

            sections = []

            for sheet in extracted_sheets:

                cell_references = []

                for row in sheet["rows"]:

                    for cell in row["cells"]:

                        cell_references.append(
                            {
                                "type": "cell",
                                "cell_reference": cell[
                                    "cell_reference"
                                ],
                                "row_number": cell["row_number"],
                                "column_number": cell[
                                    "column_number"
                                ],
                            }
                        )

                sections.append(
                    {
                        "section_type": "worksheet",
                        "section_name": sheet[
                            "worksheet_name"
                        ],
                        "content": sheet,
                        "references": cell_references,
                    }
                )

            return {
                "source_filename": file_path.name,
                "file_type": "xlsx",
                "sections": sections,
            }

        else:

            raise DocumentProcessingError(
                f"Unsupported document format: {extension}"
            )

    except (
        PDFExtractionError,
        ExcelExtractionError,
    ) as exc:

        raise DocumentProcessingError(
            str(exc)
        ) from exc

    except DocumentProcessingError:
        raise

    except Exception as exc:

        raise DocumentProcessingError(
            "Unable to process document"
        ) from exc
