
"""Tests for the shared invoice extraction and evidence schemas."""

import pytest
from pydantic import ValidationError

from app.schemas.invoice import (
    Evidence,
    EvidenceReference,
    ExtractionSource,
    InvoiceExtraction,
    InvoiceField,
    ReviewStatus,
    ValidationStatus,
)


def test_valid_pdf_page_reference():
    """A PDF reference must identify a valid page number."""
    reference = EvidenceReference(
        type="page",
        page_number=1,
    )

    assert reference.type == "page"
    assert reference.page_number == 1


def test_valid_excel_cell_reference():
    """An Excel reference must identify its cell."""
    reference = EvidenceReference(
        type="cell",
        sheet_name="Sheet1",
        cell_reference="B12",
    )

    assert reference.type == "cell"
    assert reference.cell_reference == "B12"


def test_page_reference_requires_page_number():
    """A page reference without a page number is invalid."""
    with pytest.raises(ValidationError):
        EvidenceReference(type="page")


def test_cell_reference_requires_cell_reference():
    """A cell reference without a cell address is invalid."""
    with pytest.raises(ValidationError):
        EvidenceReference(
            type="cell",
            sheet_name="Sheet1",
        )


def test_page_number_must_be_positive():
    """Page numbering starts at one, not zero."""
    with pytest.raises(ValidationError):
        EvidenceReference(
            type="page",
            page_number=0,
        )


def test_invalid_reference_type_is_rejected():
    """Only supported source reference types are accepted."""
    with pytest.raises(ValidationError):
        EvidenceReference(
            type="paragraph",
        )


def test_evidence_preserves_exact_source_text():
    """Evidence must preserve the supplied source text."""
    evidence = Evidence(
        text="Invoice Number: INV-1001",
        reference=EvidenceReference(
            type="page",
            page_number=1,
        ),
    )

    assert evidence.text == "Invoice Number: INV-1001"
    assert evidence.reference.page_number == 1


def test_empty_evidence_text_is_rejected():
    """An evidence item cannot contain an empty string."""
    with pytest.raises(ValidationError):
        Evidence(text="")


def test_invoice_field_defaults():
    """New fields start empty and await extraction and review."""
    field = InvoiceField()

    assert field.value is None
    assert field.normalized_value is None
    assert field.references == []
    assert field.evidence == []
    assert field.confidence is None
    assert field.validation_status == ValidationStatus.PENDING
    assert field.review_status == ReviewStatus.PENDING


@pytest.mark.parametrize("confidence", [-0.1, 1.1])
def test_confidence_outside_range_is_rejected(confidence):
    """Confidence must remain within the zero-to-one range."""
    with pytest.raises(ValidationError):
        InvoiceField(confidence=confidence)


@pytest.mark.parametrize("confidence", [0.0, 0.5, 1.0])
def test_valid_confidence_values_are_accepted(confidence):
    """Boundary and intermediate confidence values are valid."""
    field = InvoiceField(confidence=confidence)

    assert field.confidence == confidence


def test_confidence_does_not_accept_boolean():
    """Boolean values must not be mistaken for confidence scores."""
    with pytest.raises(ValidationError):
        InvoiceField(confidence=True)


def test_invoice_extraction_initializes_all_supported_fields():
    """The MVP invoice contract always exposes all nine fields."""
    invoice = InvoiceExtraction(document_type="invoice")

    assert invoice.document_type == "invoice"
    assert len(invoice.fields.model_fields_set) == 0
    assert invoice.fields.invoice_number.value is None
    assert invoice.fields.invoice_date.value is None
    assert invoice.fields.due_date.value is None
    assert invoice.fields.vendor_name.value is None
    assert invoice.fields.customer_name.value is None
    assert invoice.fields.subtotal.value is None
    assert invoice.fields.tax_amount.value is None
    assert invoice.fields.total_amount.value is None
    assert invoice.fields.currency.value is None


def test_unknown_document_type_is_rejected():
    """Only invoice and unknown document classifications are supported."""
    with pytest.raises(ValidationError):
        InvoiceExtraction(document_type="receipt")


def test_unknown_field_properties_are_rejected():
    """Unexpected properties must not silently enter the schema."""
    with pytest.raises(ValidationError):
        InvoiceField(unexpected_property="not supported")


def test_extraction_source_is_preserved():
    """The extraction method must be represented explicitly."""
    field = InvoiceField(source=ExtractionSource.AI)

    assert field.source == ExtractionSource.AI


def test_review_status_can_be_updated():
    """A field can move from pending to an approved state."""
    field = InvoiceField()
    field.review_status = ReviewStatus.APPROVED

    assert field.review_status == ReviewStatus.APPROVED


def test_original_and_normalized_values_remain_separate():
    """Normalization must not overwrite the original extracted value."""
    field = InvoiceField(
        value="1,250.00",
        normalized_value="1250.00",
    )

    assert field.value == "1,250.00"
    assert field.normalized_value == "1250.00"


def test_multiple_evidence_items_are_supported():
    """A field can have multiple supporting source locations."""
    field = InvoiceField(
        value="INV-1001",
        evidence=[
            Evidence(
                text="Invoice No: INV-1001",
                reference=EvidenceReference(
                    type="page",
                    page_number=1,
                ),
            ),
            Evidence(
                text="Reference: INV-1001",
                reference=EvidenceReference(
                    type="page",
                    page_number=2,
                ),
            ),
        ],
    )

    assert len(field.evidence) == 2
    assert field.evidence[0].reference.page_number == 1
    assert field.evidence[1].reference.page_number == 2


# ---------------------------------------------------------------------------
# Serialization and deserialization contract tests
# ---------------------------------------------------------------------------


def test_invoice_serializes_to_json():
    """An invoice extraction can be serialized into JSON."""
    invoice = InvoiceExtraction(
        document_type="invoice",
        fields={
            "invoice_number": InvoiceField(
                value="INV-1001",
                normalized_value="INV-1001",
                source=ExtractionSource.RULE_BASED,
                confidence=0.95,
                evidence=[
                    Evidence(
                        text="Invoice Number: INV-1001",
                        reference=EvidenceReference(
                            type="page",
                            page_number=1,
                        ),
                    )
                ],
            )
        },
    )

    serialized = invoice.model_dump_json()

    assert isinstance(serialized, str)
    assert '"document_type":"invoice"' in serialized
    assert '"INV-1001"' in serialized


def test_invoice_can_be_reconstructed_from_json():
    """A serialized invoice can be reconstructed as a validated model."""
    original = InvoiceExtraction(
        document_type="invoice",
        fields={
            "invoice_number": InvoiceField(
                value="INV-1001",
                normalized_value="INV-1001",
                source=ExtractionSource.AI,
            )
        },
    )

    serialized = original.model_dump_json()
    reconstructed = InvoiceExtraction.model_validate_json(serialized)

    assert reconstructed.document_type == original.document_type
    assert reconstructed.fields.invoice_number.value == "INV-1001"
    assert reconstructed.fields.invoice_number.normalized_value == "INV-1001"
    assert reconstructed.fields.invoice_number.source == ExtractionSource.AI


def test_json_round_trip_preserves_evidence_and_page_reference():
    """Exact evidence text and its PDF page survive a JSON round trip."""
    original = InvoiceExtraction(
        document_type="invoice",
        fields={
            "invoice_number": InvoiceField(
                value="INV-1001",
                evidence=[
                    Evidence(
                        text="Invoice Number: INV-1001",
                        reference=EvidenceReference(
                            type="page",
                            page_number=3,
                        ),
                    )
                ],
            )
        },
    )

    reconstructed = InvoiceExtraction.model_validate_json(
        original.model_dump_json()
    )

    field = reconstructed.fields.invoice_number

    assert field.evidence[0].text == "Invoice Number: INV-1001"
    assert field.evidence[0].reference.type == "page"
    assert field.evidence[0].reference.page_number == 3


def test_json_round_trip_preserves_excel_cell_reference():
    """Spreadsheet evidence retains its worksheet and cell location."""
    original = InvoiceExtraction(
        document_type="invoice",
        fields={
            "total_amount": InvoiceField(
                value="1250.00",
                evidence=[
                    Evidence(
                        text="Grand Total: 1250.00",
                        reference=EvidenceReference(
                            type="cell",
                            sheet_name="Invoice",
                            cell_reference="F24",
                        ),
                    )
                ],
            )
        },
    )

    reconstructed = InvoiceExtraction.model_validate_json(
        original.model_dump_json()
    )

    reference = reconstructed.fields.total_amount.evidence[0].reference

    assert reference.type == "cell"
    assert reference.sheet_name == "Invoice"
    assert reference.cell_reference == "F24"


def test_json_round_trip_preserves_multiple_evidence_items():
    """A field can retain evidence from multiple document locations."""
    original = InvoiceExtraction(
        document_type="invoice",
        fields={
            "invoice_number": InvoiceField(
                value="INV-1001",
                evidence=[
                    Evidence(
                        text="Invoice No: INV-1001",
                        reference=EvidenceReference(
                            type="page",
                            page_number=1,
                        ),
                    ),
                    Evidence(
                        text="Reference: INV-1001",
                        reference=EvidenceReference(
                            type="page",
                            page_number=2,
                        ),
                    ),
                ],
            )
        },
    )

    reconstructed = InvoiceExtraction.model_validate_json(
        original.model_dump_json()
    )

    evidence = reconstructed.fields.invoice_number.evidence

    assert len(evidence) == 2
    assert evidence[0].text == "Invoice No: INV-1001"
    assert evidence[1].text == "Reference: INV-1001"
    assert evidence[0].reference.page_number == 1
    assert evidence[1].reference.page_number == 2


def test_json_round_trip_preserves_review_and_validation_states():
    """Workflow states survive serialization and reconstruction."""
    original = InvoiceExtraction(
        document_type="invoice",
        fields={
            "total_amount": InvoiceField(
                value="1250.00",
                normalized_value="1250.00",
                validation_status=ValidationStatus.VALID,
                review_status=ReviewStatus.APPROVED,
            )
        },
    )

    reconstructed = InvoiceExtraction.model_validate_json(
        original.model_dump_json()
    )

    field = reconstructed.fields.total_amount

    assert field.validation_status == ValidationStatus.VALID
    assert field.review_status == ReviewStatus.APPROVED


def test_json_round_trip_preserves_missing_confidence_as_null():
    """Unknown confidence must remain null, not become an invented score."""
    original = InvoiceExtraction(
        document_type="invoice",
        fields={
            "vendor_name": InvoiceField(
                value="Example Company",
                source=ExtractionSource.AI,
                confidence=None,
            )
        },
    )

    serialized = original.model_dump_json()
    reconstructed = InvoiceExtraction.model_validate_json(serialized)

    assert reconstructed.fields.vendor_name.confidence is None
    assert '"confidence":null' in serialized


def test_json_round_trip_preserves_original_and_normalized_values():
    """The extracted value must remain separate from its normalized form."""
    original = InvoiceExtraction(
        document_type="invoice",
        fields={
            "subtotal": InvoiceField(
                value="1,250.00",
                normalized_value="1250.00",
                normalization_status="normalized",
            )
        },
    )

    reconstructed = InvoiceExtraction.model_validate_json(
        original.model_dump_json()
    )

    field = reconstructed.fields.subtotal

    assert field.value == "1,250.00"
    assert field.normalized_value == "1250.00"
    assert field.normalization_status == "normalized"


def test_unknown_json_properties_are_rejected_during_reconstruction():
    """Invalid or unexpected JSON properties cannot bypass schema validation."""
    invalid_json = """
    {
        "document_type": "invoice",
        "unexpected_property": "not supported",
        "fields": {}
    }
    """

    with pytest.raises(ValidationError):
        InvoiceExtraction.model_validate_json(invalid_json)


# ---------------------------------------------------------------------------
# Existing extractor compatibility tests
# ---------------------------------------------------------------------------

from datetime import date, datetime


def test_excel_extractor_worksheet_name_is_accepted():
    """The schema accepts the worksheet_name used by the Excel extractor."""
    reference = EvidenceReference.model_validate(
        {
            "type": "cell",
            "worksheet_name": "Invoice",
            "cell_reference": "F24",
        }
    )

    assert reference.sheet_name == "Invoice"
    assert reference.cell_reference == "F24"


def test_legacy_sheet_name_is_still_accepted():
    """Existing callers using sheet_name remain compatible."""
    reference = EvidenceReference(
        type="cell",
        sheet_name="Invoice",
        cell_reference="F24",
    )

    assert reference.sheet_name == "Invoice"


def test_excel_reference_accepts_row_and_column_numbers():
    """Spreadsheet references can retain numeric cell coordinates."""
    reference = EvidenceReference.model_validate(
        {
            "type": "cell",
            "worksheet_name": "Invoice",
            "cell_reference": "F24",
            "row_number": 24,
            "column_number": 6,
        }
    )

    assert reference.row_number == 24
    assert reference.column_number == 6


@pytest.mark.parametrize("coordinate", ["row_number", "column_number"])
def test_excel_reference_rejects_zero_coordinates(coordinate):
    """Excel row and column numbers must be positive."""
    reference_data = {
        "type": "cell",
        "cell_reference": "A1",
        coordinate: 0,
    }

    with pytest.raises(ValidationError):
        EvidenceReference.model_validate(reference_data)


def test_excel_extractor_reference_round_trip():
    """The actual Excel reference shape survives JSON serialization."""
    original = EvidenceReference.model_validate(
        {
            "type": "cell",
            "worksheet_name": "Sales Invoice",
            "cell_reference": "F24",
        }
    )

    reconstructed = EvidenceReference.model_validate_json(
        original.model_dump_json()
    )

    assert reconstructed.type == "cell"
    assert reconstructed.sheet_name == "Sales Invoice"
    assert reconstructed.cell_reference == "F24"


def test_invoice_field_accepts_python_date_value():
    """Raw Excel date values can be represented without conversion."""
    original_date = date(2026, 11, 26)

    field = InvoiceField(value=original_date)

    assert field.value == original_date
    assert isinstance(field.value, date)
    assert not isinstance(field.value, datetime)


def test_invoice_field_accepts_python_datetime_value():
    """Raw Excel datetime values can be represented without conversion."""
    original_datetime = datetime(2026, 11, 26, 14, 30, 0)

    field = InvoiceField(value=original_datetime)

    assert field.value == original_datetime
    assert isinstance(field.value, datetime)


def test_date_value_serializes_to_iso_string():
    """JSON represents native Python dates using ISO date notation."""
    field = InvoiceField(value=date(2026, 11, 26))

    serialized = field.model_dump(mode="json")

    assert serialized["value"] == "2026-11-26"


def test_datetime_value_serializes_to_iso_string():
    """JSON represents native Python datetimes using ISO notation."""
    field = InvoiceField(
        value=datetime(2026, 11, 26, 14, 30, 0)
    )

    serialized = field.model_dump(mode="json")

    assert serialized["value"] == "2026-11-26T14:30:00"


def test_date_json_round_trip_preserves_original_representation():
    """A serialized date remains an ISO string after JSON reconstruction."""
    original = InvoiceField(value=date(2026, 11, 26))

    reconstructed = InvoiceField.model_validate_json(
        original.model_dump_json()
    )

    assert reconstructed.value == "2026-11-26"
    assert isinstance(reconstructed.value, str)


def test_datetime_json_round_trip_preserves_original_representation():
    """A serialized datetime remains an ISO string after reconstruction."""
    original = InvoiceField(
        value=datetime(2026, 11, 26, 14, 30, 0)
    )

    reconstructed = InvoiceField.model_validate_json(
        original.model_dump_json()
    )

    assert reconstructed.value == "2026-11-26T14:30:00"
    assert isinstance(reconstructed.value, str)


# ---------------------------------------------------------------------------
# Extraction-to-invoice-contract adapter tests
# ---------------------------------------------------------------------------

from copy import deepcopy

from app.document_processing.invoice_contract_adapter import (
    InvoiceContractAdapterError,
    build_invoice_extraction,
)


def make_rule_based_processor_result():
    """Build a representative result using the existing processor structure."""

    raw_fields = {
        "invoice_number": {
            "value": "INV-1001",
            "references": [
                {"type": "page", "page_number": 1}
            ],
        },
        "invoice_date": {
            "value": "24 November 2026",
            "references": [
                {"type": "page", "page_number": 1}
            ],
        },
        "vendor_name": {
            "value": "Example Supplies Ltd",
            "references": [
                {
                    "type": "cell",
                    "worksheet_name": "Invoice",
                    "cell_reference": "B3",
                }
            ],
        },
        "total_amount": {
            "value": 1250.00,
            "references": [
                {
                    "type": "cell",
                    "worksheet_name": "Invoice",
                    "cell_reference": "F24",
                }
            ],
        },
    }

    normalized_fields = {}

    for field_name, field_data in raw_fields.items():
        normalized_fields[field_name] = {
            "value": field_data["value"],
            "normalized_value": (
                "2026-11-24"
                if field_name == "invoice_date"
                else "1250"
                if field_name == "total_amount"
                else field_data["value"]
            ),
            "normalization_status": "normalized",
            "references": deepcopy(field_data["references"]),
        }

    return {
        "file_type": "xlsx",
        "business_fields": {
            "document_type": "invoice",
            "fields": raw_fields,
        },
        "normalized_business_fields": {
            "document_type": "invoice",
            "fields": normalized_fields,
        },
        "ai_extraction": {
            "status": "disabled",
            "fields": None,
            "normalized_fields": None,
            "comparison": None,
            "error": None,
        },
    }


def make_ai_processor_result():
    """Build a representative completed AI extraction result."""

    ai_fields = {
        "document_type": "invoice",
        "fields": {
            "invoice_number": {
                "value": "AI-2001",
                "references": [],
            },
            "total_amount": {
                "value": 500.00,
                "references": [],
            },
        },
    }

    normalized_fields = {
        "document_type": "invoice",
        "fields": {
            "invoice_number": {
                "value": "AI-2001",
                "normalized_value": "AI-2001",
                "normalization_status": "normalized",
                "references": [],
            },
            "total_amount": {
                "value": 500.00,
                "normalized_value": "500",
                "normalization_status": "normalized",
                "references": [],
            },
        },
    }

    return {
        "ai_extraction": {
            "status": "completed",
            "fields": ai_fields,
            "normalized_fields": normalized_fields,
            "comparison": None,
            "error": None,
        }
    }


def test_adapter_converts_rule_based_extraction():
    """Rule-based extraction can be converted into the shared contract."""

    result = build_invoice_extraction(
        make_rule_based_processor_result()
    )

    assert result.document_type == "invoice"

    field = result.fields.invoice_number

    assert field.value == "INV-1001"
    assert field.normalized_value == "INV-1001"
    assert field.source == ExtractionSource.RULE_BASED


def test_adapter_converts_normalized_date():
    """Original and normalized date values remain separate."""

    result = build_invoice_extraction(
        make_rule_based_processor_result()
    )

    field = result.fields.invoice_date

    assert field.value == "24 November 2026"
    assert field.normalized_value == "2026-11-24"
    assert field.normalization_status == "normalized"


def test_adapter_preserves_pdf_page_reference():
    """PDF page references survive conversion."""

    result = build_invoice_extraction(
        make_rule_based_processor_result()
    )

    references = result.fields.invoice_number.references

    assert len(references) == 1
    assert references[0].type == "page"
    assert references[0].page_number == 1


def test_adapter_preserves_excel_reference():
    """Excel worksheet and cell references survive conversion."""

    result = build_invoice_extraction(
        make_rule_based_processor_result()
    )

    reference = result.fields.vendor_name.references[0]

    assert reference.type == "cell"
    assert reference.sheet_name == "Invoice"
    assert reference.cell_reference == "B3"


def test_adapter_preserves_empty_evidence_and_confidence():
    """Missing evidence and confidence are never invented."""

    result = build_invoice_extraction(
        make_rule_based_processor_result()
    )

    field = result.fields.invoice_number

    assert field.evidence == []
    assert field.confidence is None


def test_adapter_initializes_all_nine_invoice_fields():
    """The converted result always contains the complete MVP field set."""

    result = build_invoice_extraction(
        make_rule_based_processor_result()
    )

    assert len(result.fields.model_fields_set) == 9


def test_adapter_handles_missing_fields():
    """Fields absent from an extraction result remain empty."""

    result = build_invoice_extraction(
        make_rule_based_processor_result()
    )

    assert result.fields.customer_name.value is None
    assert result.fields.customer_name.normalized_value is None
    assert result.fields.customer_name.references == []


def test_adapter_converts_ai_extraction():
    """Completed AI extraction can be converted independently."""

    result = build_invoice_extraction(
        make_ai_processor_result(),
        source="ai",
    )

    field = result.fields.invoice_number

    assert field.value == "AI-2001"
    assert field.source == ExtractionSource.AI
    assert field.references == []
    assert field.evidence == []
    assert field.confidence is None


def test_adapter_preserves_unknown_document_type():
    """An unknown classification is retained rather than changed."""

    processor_result = make_rule_based_processor_result()
    processor_result["business_fields"]["document_type"] = "unknown"
    processor_result["normalized_business_fields"]["document_type"] = (
        "unknown"
    )

    result = build_invoice_extraction(processor_result)

    assert result.document_type == "unknown"


def test_adapter_does_not_modify_original_processor_result():
    """Conversion must not mutate the existing processing output."""

    processor_result = make_rule_based_processor_result()
    original = deepcopy(processor_result)

    build_invoice_extraction(processor_result)

    assert processor_result == original


def test_adapter_rejects_ai_when_disabled():
    """Disabled AI extraction cannot be converted as an AI result."""

    processor_result = make_rule_based_processor_result()

    with pytest.raises(InvoiceContractAdapterError):
        build_invoice_extraction(
            processor_result,
            source="ai",
        )


def test_adapter_rejects_ai_when_failed():
    """Failed AI extraction cannot be treated as completed output."""

    processor_result = make_ai_processor_result()
    processor_result["ai_extraction"]["status"] = "failed"

    with pytest.raises(InvoiceContractAdapterError):
        build_invoice_extraction(
            processor_result,
            source="ai",
        )


def test_adapter_rejects_invalid_source():
    """Only the explicitly supported extraction sources are accepted."""

    with pytest.raises(InvoiceContractAdapterError):
        build_invoice_extraction(
            make_rule_based_processor_result(),
            source="unknown_source",
        )


def test_adapter_rejects_invalid_page_reference():
    """Malformed source references must not silently enter the contract."""

    processor_result = make_rule_based_processor_result()

    processor_result["business_fields"]["fields"]["invoice_number"][
        "references"
    ] = [{"type": "page"}]

    with pytest.raises(InvoiceContractAdapterError):
        build_invoice_extraction(processor_result)


def test_adapter_json_round_trip():
    """The converted contract remains serializable and reconstructable."""

    original = build_invoice_extraction(
        make_rule_based_processor_result()
    )

    reconstructed = InvoiceExtraction.model_validate_json(
        original.model_dump_json()
    )

    assert reconstructed.document_type == "invoice"
    assert reconstructed.fields.invoice_number.value == "INV-1001"
    assert (
        reconstructed.fields.invoice_number.references[0].page_number
        == 1
    )
