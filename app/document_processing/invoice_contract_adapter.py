
"""
Adapter between the existing extraction pipeline and the shared invoice schema.

The adapter converts existing extraction results into InvoiceExtraction models.

It does not:
- Extract document content.
- Call an AI provider.
- Normalize values.
- Invent evidence or confidence scores.
- Modify the original extraction results.
"""

from enum import Enum

from app.schemas.invoice import (
    ExtractionSource,
    EvidenceReference,
    InvoiceExtraction,
    InvoiceField,
)


class InvoiceContractAdapterError(ValueError):
    """Raised when an extraction result cannot be mapped to the invoice contract."""


# Keep this list aligned with the MVP invoice schema.
SUPPORTED_INVOICE_FIELDS = (
    "invoice_number",
    "invoice_date",
    "due_date",
    "vendor_name",
    "customer_name",
    "subtotal",
    "tax_amount",
    "total_amount",
    "currency",
)


class ExtractionSelection(str, Enum):
    """Identifies which extraction result should be converted."""

    RULE_BASED = "rule_based"
    AI = "ai"


def _get_extraction_payload(
    extraction_result: dict,
    selection: ExtractionSelection,
) -> tuple[dict, dict]:
    """
    Retrieve the raw and normalized fields for the selected extractor.

    Returns:
        (raw_extraction, normalized_extraction)
    """

    if selection == ExtractionSelection.RULE_BASED:

        raw_extraction = extraction_result.get("business_fields")
        normalized_extraction = extraction_result.get(
            "normalized_business_fields"
        )

    elif selection == ExtractionSelection.AI:

        ai_result = extraction_result.get("ai_extraction")

        if not isinstance(ai_result, dict):
            raise InvoiceContractAdapterError(
                "AI extraction result is missing or invalid."
            )

        if ai_result.get("status") != "completed":
            raise InvoiceContractAdapterError(
                "AI extraction must be completed before conversion. "
                f"Current status: {ai_result.get('status')!r}"
            )

        raw_extraction = ai_result.get("fields")
        normalized_extraction = ai_result.get("normalized_fields")

    else:
        raise InvoiceContractAdapterError(
            f"Unsupported extraction selection: {selection!r}"
        )

    if not isinstance(raw_extraction, dict):
        raise InvoiceContractAdapterError(
            "Raw extraction result must be a dictionary."
        )

    if not isinstance(normalized_extraction, dict):
        raise InvoiceContractAdapterError(
            "Normalized extraction result must be a dictionary."
        )

    if not isinstance(raw_extraction.get("fields"), dict):
        raise InvoiceContractAdapterError(
            "Raw extraction result must contain a fields dictionary."
        )

    if not isinstance(normalized_extraction.get("fields"), dict):
        raise InvoiceContractAdapterError(
            "Normalized extraction result must contain a fields dictionary."
        )

    return raw_extraction, normalized_extraction


def _convert_references(references: list) -> list[EvidenceReference]:
    """
    Convert existing PDF and Excel references into schema models.

    Existing reference formats are preserved:
    - PDF: type and page_number
    - Excel: type, worksheet_name, and cell_reference

    Additional supported coordinates are retained when available.
    """

    if not isinstance(references, list):
        raise InvoiceContractAdapterError(
            "Field references must be provided as a list."
        )

    converted_references = []

    for reference in references:

        if not isinstance(reference, dict):
            raise InvoiceContractAdapterError(
                "Each field reference must be a dictionary."
            )

        try:
            converted_reference = EvidenceReference.model_validate(reference)

        except Exception as exc:
            raise InvoiceContractAdapterError(
                f"Invalid field reference: {reference!r}"
            ) from exc

        converted_references.append(converted_reference)

    return converted_references


def _convert_field(
    field_name: str,
    raw_field: dict,
    normalized_field: dict,
    source: ExtractionSource,
) -> InvoiceField:
    """
    Convert one existing business field into an InvoiceField model.
    """

    if not isinstance(raw_field, dict):
        raise InvoiceContractAdapterError(
            f"Raw field must be a dictionary: {field_name}"
        )

    if not isinstance(normalized_field, dict):
        raise InvoiceContractAdapterError(
            f"Normalized field must be a dictionary: {field_name}"
        )

    references = _convert_references(
        raw_field.get("references", [])
    )

    return InvoiceField(
        value=raw_field.get("value"),
        normalized_value=normalized_field.get("normalized_value"),
        normalization_status=normalized_field.get(
            "normalization_status"
        ),
        references=references,

        # The current extraction pipeline does not produce exact
        # evidence text. Do not manufacture evidence.
        evidence=[],

        # The source is known, but the pipeline does not provide
        # calibrated confidence scores.
        source=source,
        confidence=None,
    )


def build_invoice_extraction(
    extraction_result: dict,
    source: ExtractionSelection | str = ExtractionSelection.RULE_BASED,
) -> InvoiceExtraction:
    """
    Convert an existing document-processing result into InvoiceExtraction.

    Args:
        extraction_result:
            Complete dictionary returned by process_document().

        source:
            "rule_based" or "ai".

    Returns:
        A validated InvoiceExtraction model.

    The original extraction_result is never modified.
    """

    if not isinstance(extraction_result, dict):
        raise InvoiceContractAdapterError(
            "Extraction result must be a dictionary."
        )

    try:
        selection = ExtractionSelection(source)

    except (TypeError, ValueError) as exc:
        raise InvoiceContractAdapterError(
            f"Unsupported extraction source: {source!r}"
        ) from exc

    raw_extraction, normalized_extraction = _get_extraction_payload(
        extraction_result,
        selection,
    )

    document_type = raw_extraction.get("document_type")

    if document_type not in {"invoice", "unknown"}:
        raise InvoiceContractAdapterError(
            f"Unsupported document type: {document_type!r}"
        )

    raw_fields = raw_extraction["fields"]
    normalized_fields = normalized_extraction["fields"]

    extraction_source = ExtractionSource(selection.value)

    converted_fields = {}

    for field_name in SUPPORTED_INVOICE_FIELDS:

        raw_field = raw_fields.get(field_name, {})
        normalized_field = normalized_fields.get(field_name, {})

        converted_fields[field_name] = _convert_field(
            field_name=field_name,
            raw_field=raw_field,
            normalized_field=normalized_field,
            source=extraction_source,
        )

    return InvoiceExtraction(
        document_type=document_type,
        fields=converted_fields,
    )
