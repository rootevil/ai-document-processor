import json

import pytest

from app.document_processing.ai_extraction_service import (
    AI_INVOICE_FIELDS,
    AIExtractionError,
    build_document_text,
    build_invoice_extraction_prompt,
    parse_ai_response,
    compare_business_fields,
    extract_invoice_fields_with_ai,
)


class FakeAIProvider:
    """
    Fake provider for testing.

    It returns a predefined response instead of contacting Ollama.
    """

    def __init__(self, response):

        self.response = response

        self.received_prompt = None

    def generate_json(self, prompt):

        self.received_prompt = prompt

        return self.response


def create_valid_ai_response():

    return {
        "document_type": "invoice",
        "fields": {
            "invoice_number": "INV-1001",
            "invoice_date": "2026-11-24",
            "due_date": None,
            "vendor_name": "ABC Supplies",
            "customer_name": "ABC Technologies",
            "subtotal": 1000,
            "tax_amount": 150,
            "total_amount": 1150,
            "currency": "PKR",
        },
    }


def create_sample_extraction_result():

    return {
        "source_filename": "sample_invoice.pdf",
        "file_type": "pdf",
        "sections": [
            {
                "section_type": "page",
                "section_name": "1",
                "content": {
                    "text": (
                        "INVOICE\n"
                        "Invoice Number: INV-1001\n"
                        "Invoice Date: 2026-11-24\n"
                        "Subtotal: 1000\n"
                        "Total: 1150"
                    )
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


def test_build_document_text_from_pdf():

    result = build_document_text(
        create_sample_extraction_result()
    )

    assert "Page 1" in result

    assert "INV-1001" in result

    assert "2026-11-24" in result


def test_build_document_text_from_excel():

    extraction_result = {
        "file_type": "xlsx",
        "sections": [
            {
                "section_type": "worksheet",
                "section_name": "Invoice",
                "content": {
                    "rows": [
                        {
                            "cells": [
                                {
                                    "cell_reference": "A2",
                                    "value": "Invoice Number",
                                    "data_type": "s",
                                },
                                {
                                    "cell_reference": "B2",
                                    "value": "INV-1001",
                                    "data_type": "s",
                                },
                                {
                                    "cell_reference": "D8",
                                    "value": "=SUM(B6:B7)",
                                    "data_type": "f",
                                },
                            ]
                        }
                    ]
                },
            }
        ],
    }

    result = build_document_text(
        extraction_result
    )

    assert "Invoice" in result

    assert "B2: INV-1001" in result

    # Formula cells must not be included.
    assert "=SUM(B6:B7)" not in result


def test_build_prompt_contains_supported_fields():

    prompt = build_invoice_extraction_prompt(
        "Invoice Number: INV-1001"
    )

    for field_name in AI_INVOICE_FIELDS:

        assert field_name in prompt

    assert "DOCUMENT CONTENT START" in prompt

    assert "DOCUMENT CONTENT END" in prompt


def test_parse_valid_ai_response():

    response = json.dumps(
        create_valid_ai_response()
    )

    result = parse_ai_response(response)

    assert result["document_type"] == "invoice"

    assert (
        result["fields"]["invoice_number"]["value"]
        == "INV-1001"
    )

    assert (
        result["fields"]["total_amount"]["value"]
        == 1150
    )

    # The AI must not invent source references.
    assert (
        result["fields"]["invoice_number"]["references"]
        == []
    )


def test_parse_response_fills_missing_fields():

    response = json.dumps(
        {
            "document_type": "invoice",
            "fields": {
                "invoice_number": "INV-1001",
            },
        }
    )

    result = parse_ai_response(response)

    assert (
        result["fields"]["invoice_number"]["value"]
        == "INV-1001"
    )

    assert (
        result["fields"]["total_amount"]["value"]
        is None
    )


def test_parse_invalid_json():

    with pytest.raises(AIExtractionError):

        parse_ai_response(
            "This is not JSON"
        )


def test_parse_non_dictionary_response():

    with pytest.raises(AIExtractionError):

        parse_ai_response(
            '["invoice", "INV-1001"]'
        )


def test_parse_invalid_document_type():

    response = json.dumps(
        {
            "document_type": "receipt",
            "fields": {},
        }
    )

    with pytest.raises(AIExtractionError):

        parse_ai_response(response)


def test_parse_rejects_nested_field_values():

    response = json.dumps(
        {
            "document_type": "invoice",
            "fields": {
                "invoice_number": {
                    "unexpected": "object",
                }
            },
        }
    )

    with pytest.raises(AIExtractionError):

        parse_ai_response(response)


def test_parse_rejects_boolean_field_values():

    response = json.dumps(
        {
            "document_type": "invoice",
            "fields": {
                "invoice_number": True,
            },
        }
    )

    with pytest.raises(AIExtractionError):

        parse_ai_response(response)


def test_compare_matching_values():

    rule_based = {
        "fields": {
            "invoice_number": {
                "value": "INV-1001",
            }
        }
    }

    ai_fields = {
        "fields": {
            "invoice_number": {
                "value": "INV-1001",
            }
        }
    }

    result = compare_business_fields(
        rule_based,
        ai_fields,
    )

    assert (
        result["invoice_number"]["status"]
        == "matched"
    )


def test_compare_conflicting_values():

    rule_based = {
        "fields": {
            "invoice_number": {
                "value": "INV-1001",
            }
        }
    }

    ai_fields = {
        "fields": {
            "invoice_number": {
                "value": "INV-2001",
            }
        }
    }

    result = compare_business_fields(
        rule_based,
        ai_fields,
    )

    assert (
        result["invoice_number"]["status"]
        == "conflict"
    )


def test_compare_ai_only_value():

    rule_based = {
        "fields": {
            "invoice_number": {
                "value": None,
            }
        }
    }

    ai_fields = {
        "fields": {
            "invoice_number": {
                "value": "INV-1001",
            }
        }
    }

    result = compare_business_fields(
        rule_based,
        ai_fields,
    )

    assert (
        result["invoice_number"]["status"]
        == "ai_only"
    )


def test_compare_rule_based_only_value():

    rule_based = {
        "fields": {
            "invoice_number": {
                "value": "INV-1001",
            }
        }
    }

    ai_fields = {
        "fields": {
            "invoice_number": {
                "value": None,
            }
        }
    }

    result = compare_business_fields(
        rule_based,
        ai_fields,
    )

    assert (
        result["invoice_number"]["status"]
        == "rule_based_only"
    )


def test_compare_missing_values():

    result = compare_business_fields(
        {"fields": {}},
        {"fields": {}},
    )

    assert (
        result["invoice_number"]["status"]
        == "missing"
    )


def test_ai_extraction_uses_injected_provider():

    provider = FakeAIProvider(
        json.dumps(create_valid_ai_response())
    )

    result = extract_invoice_fields_with_ai(
        create_sample_extraction_result(),
        provider=provider,
    )

    assert result["document_type"] == "invoice"

    assert (
        result["fields"]["invoice_number"]["value"]
        == "INV-1001"
    )

    assert provider.received_prompt is not None

    assert "INV-1001" in provider.received_prompt


def test_ai_extraction_rejects_empty_document():

    provider = FakeAIProvider("{}")

    with pytest.raises(AIExtractionError):

        extract_invoice_fields_with_ai(
            {
                "file_type": "pdf",
                "sections": [],
            },
            provider=provider,
        )


def test_ai_extraction_rejects_excessively_large_document():

    extraction_result = {
        "file_type": "pdf",
        "sections": [
            {
                "section_type": "page",
                "section_name": "1",
                "content": {
                    "text": "A" * 40001,
                },
            }
        ],
    }

    provider = FakeAIProvider("{}")

    with pytest.raises(AIExtractionError):

        extract_invoice_fields_with_ai(
            extraction_result,
            provider=provider,
        )