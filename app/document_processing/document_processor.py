
"""
Main document-processing module.

Responsibilities:
1. Identify supported document formats.
2. Extract raw PDF or Excel contents.
3. Convert extracted contents into a unified structure.
4. Extract meaningful invoice business fields.
5. Preserve original document references.

Supported formats:
    - PDF
    - XLSX
"""

from pathlib import Path

from app.document_processing.pdf_extractor import (
    extract_pdf_text,
    PDFExtractionError,
)

from app.document_processing.excel_extractor import (
    extract_excel_data,
    ExcelExtractionError,
)

from app.document_processing.business_field_extractor import (
    extract_invoice_fields,
    BusinessFieldExtractionError,
)

# Import the value-normalization layer.
#
# This module standardizes extracted business values
# without modifying the original extraction result.
from app.document_processing.value_normalizer import (
    normalize_business_fields,
    BusinessFieldNormalizationError,
)

class DocumentProcessingError(Exception):
    """Raised when document processing fails."""


def process_document(file_path: Path) -> dict:
    """
    Process a supported document and return a unified result.

    The function first extracts the original document contents.

    It then performs business-field extraction using the
    unified result produced by the raw extraction layer.

    Original sections and references are preserved.
    """

    # STEP 1:
    # Confirm that the requested document exists.
    if not file_path.is_file():

        raise DocumentProcessingError(
            "Document file not found"
        )

    extension = file_path.suffix.lower()

    try:

        # STEP 2:
        # Process PDF documents.
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

            extraction_result = {
                "source_filename": file_path.name,
                "file_type": "pdf",
                "sections": sections,
            }

        # STEP 3:
        # Process Excel documents.
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

            extraction_result = {
                "source_filename": file_path.name,
                "file_type": "xlsx",
                "sections": sections,
            }

        # STEP 4:
        # Reject unsupported document formats.
        else:

            raise DocumentProcessingError(
                f"Unsupported document format: {extension}"
            )

       # STEP 5:
       # Extract meaningful business fields from the document.
        business_fields = extract_invoice_fields(
            extraction_result
        )

        # STEP 6:
        # Normalize the extracted business values.
        #
        # The original business_fields structure is preserved.
        # The normalizer creates a separate result containing
        # both original and standardized values.
        normalized_business_fields = normalize_business_fields(
            business_fields
        )

        # STEP 7:
        # Store both extraction results.
        #
        # business_fields:
        #     Original values extracted from the document.
        #
        # normalized_business_fields:
        # Standardized values with normalization statuses.
        extraction_result["business_fields"] = business_fields

        extraction_result["normalized_business_fields"] = (
            normalized_business_fields
        )

    except (
        PDFExtractionError,
        ExcelExtractionError,
        BusinessFieldExtractionError,
        BusinessFieldNormalizationError,
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

    except (
        PDFExtractionError,
        ExcelExtractionError,
        BusinessFieldExtractionError,
        BusinessFieldNormalizationError,
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

    # STEP 8:
    # Return the complete extraction result.
    #
    # This includes:
    # 1. Original document sections.
    # 2. Original extracted business fields.
    # 3. Normalized business fields.
    return extraction_result