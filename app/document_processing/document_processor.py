"""
Main document-processing module.

Responsibilities:
1. Identify supported document formats.
2. Extract raw PDF or Excel contents.
3. Convert extracted contents into a unified structure.
4. Extract business fields using rule-based extraction.
5. Normalize extracted business values.
6. Optionally extract business fields using AI.
7. Compare rule-based and AI results.
8. Preserve original document references.
"""

from pathlib import Path
import logging

from app.core.config import settings

from app.document_processing.invoice_contract_adapter import (
    build_invoice_extraction,
)

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

from app.document_processing.value_normalizer import (
    normalize_business_fields,
    BusinessFieldNormalizationError,
)

from app.document_processing.ai_extraction_service import (
    extract_invoice_fields_with_ai,
    compare_business_fields,
    AIExtractionError,
)


class DocumentProcessingError(Exception):
    """Raised when document processing fails."""


def process_document(file_path: Path) -> dict:
    """
    Process a supported document and return a unified result.

    Rule-based extraction remains the primary extraction layer.

    AI extraction is optional and controlled by application settings.

    AI failures do not prevent successful raw document processing.
    """

    # STEP 1:
    # Confirm that the document exists.
    if not file_path.is_file():

        raise DocumentProcessingError(
            "Document file not found"
        )

    extension = file_path.suffix.lower()

    try:

        # STEP 2:
        # Extract PDF content.
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
        # Extract Excel content.
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

        else:

            raise DocumentProcessingError(
                f"Unsupported document format: {extension}"
            )

        # STEP 4:
        # Extract business fields using existing rules.
        business_fields = extract_invoice_fields(
            extraction_result
        )

        # STEP 5:
        # Normalize rule-based business fields.
        normalized_business_fields = normalize_business_fields(
            business_fields
        )

        extraction_result["business_fields"] = business_fields

        extraction_result["normalized_business_fields"] = (
            normalized_business_fields
        )

        # STEP 6:
        # Initialize the AI result as disabled.
        #
        # This ensures the document processor works even when
        # Ollama is not running or AI extraction is disabled.
        extraction_result["ai_extraction"] = {
            "status": "disabled",
            "fields": None,
            "normalized_fields": None,
            "comparison": None,
            "error": None,
        }

        # STEP 7:
        # Run AI extraction only when explicitly enabled.
        if settings.ai_extraction_enabled:

            try:

                ai_fields = extract_invoice_fields_with_ai(
                    extraction_result
                )

                # Normalize the AI result separately.
                normalized_ai_fields = normalize_business_fields(
                    ai_fields
                )

                # Compare AI results against rule-based results.
                comparison = compare_business_fields(
                    business_fields,
                    ai_fields,
                )

                extraction_result["ai_extraction"] = {
                    "status": "completed",
                    "fields": ai_fields,
                    "normalized_fields": normalized_ai_fields,
                    "comparison": comparison,
                    "error": None,
                }

            except AIExtractionError as exc:

                # Log the actual AI failure for debugging.
                # This helps identify whether the issue is related
                # to Ollama, JSON parsing, or response validation.

                logging.exception(
                    "AI invoice extraction failed: %s",
                    exc,
                )

                extraction_result["ai_extraction"] = {
                    "status": "failed",
                    "fields": None,
                    "normalized_fields": None,
                    "comparison": None,
                    "error": "AI extraction could not be completed",
                }

        # STEP 8:
        # Always build the shared invoice contract from rule-based extraction.
        #
        # This runs whether AI is disabled, successful, or has failed.
        # Rule-based extraction remains the canonical result for now.
        invoice_extraction = build_invoice_extraction(
            extraction_result
        )

        # Convert the Pydantic model into JSON-compatible Python data
        # so the existing SQLite persistence can store it.
        extraction_result["invoice_extraction"] = (
            invoice_extraction.model_dump(mode="json")
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

    # STEP 8:
    # Return the complete processing result.
    return extraction_result
