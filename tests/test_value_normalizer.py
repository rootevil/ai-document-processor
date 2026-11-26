
"""
Tests for business-value normalization.

These tests verify:
1. Date normalization.
2. Ambiguous-date protection.
3. Monetary amount normalization.
4. Financial precision using Decimal.
5. Ambiguous-amount protection.
6. Currency normalization.
7. Text cleaning.
8. Missing-value handling.
9. Original-value preservation.
10. Source-reference preservation.
11. Invalid-input handling.
"""

from datetime import date, datetime

import pytest

from app.document_processing.value_normalizer import (
    normalize_text,
    normalize_date,
    parse_amount,
    normalize_currency,
    normalize_field_value,
    normalize_business_fields,
    BusinessFieldNormalizationError,
)


def test_normalize_text():
    """Leading, trailing, and repeated whitespace is removed."""

    result, status = normalize_text(
        "  ABC    Technologies  "
    )

    assert result == "ABC Technologies"

    assert status == "normalized"


def test_normalize_invoice_number():
    """Invoice identifiers retain their content while whitespace is cleaned."""

    result, status = normalize_field_value(
        "invoice_number",
        "  INV-1001  ",
    )

    assert result == "INV-1001"

    assert status == "normalized"


def test_normalize_iso_date():
    """ISO dates remain in the standard format."""

    result, status = normalize_date(
        "2026-11-24"
    )

    assert result == "2026-11-24"

    assert status == "normalized"


def test_normalize_unambiguous_day_first_date():
    """An unambiguous day-first date is converted to ISO format."""

    result, status = normalize_date(
        "24/11/2026"
    )

    assert result == "2026-11-24"

    assert status == "normalized"


def test_normalize_unambiguous_month_first_date():
    """An unambiguous month-first date is converted to ISO format."""

    result, status = normalize_date(
        "11/24/2026"
    )

    assert result == "2026-11-24"

    assert status == "normalized"


def test_ambiguous_date_requires_review():
    """Dates with two valid interpretations are not guessed."""

    result, status = normalize_date(
        "01/02/2026"
    )

    assert result is None

    assert status == "needs_review"


def test_invalid_date_requires_review():
    """Invalid calendar dates are not normalized."""

    result, status = normalize_date(
        "31/02/2026"
    )

    assert result is None

    assert status == "needs_review"


def test_normalize_date_with_month_name():
    """Dates containing written month names are supported."""

    result, status = normalize_date(
        "24 November 2026"
    )

    assert result == "2026-11-24"

    assert status == "normalized"


def test_normalize_python_date():
    """Excel date values represented by Python date objects are supported."""

    result, status = normalize_date(
        date(2026, 11, 24)
    )

    assert result == "2026-11-24"

    assert status == "normalized"


def test_normalize_python_datetime():
    """Excel datetime values are converted to their calendar date."""

    result, status = normalize_date(
        datetime(2026, 11, 24, 15, 30)
    )

    assert result == "2026-11-24"

    assert status == "normalized"


def test_normalize_integer_amount():
    """Integer amounts are represented as decimal strings."""

    result, status = parse_amount(1150)

    assert result == "1150"

    assert status == "normalized"


def test_normalize_decimal_amount():
    """Decimal amounts are normalized without floating-point conversion."""

    result, status = parse_amount("1150.00")

    assert result == "1150"

    assert status == "normalized"


def test_normalize_us_grouped_amount():
    """Standard comma-grouped amounts are normalized."""

    result, status = parse_amount("1,150.00")

    assert result == "1150"

    assert status == "normalized"


def test_normalize_european_grouped_amount():
    """European decimal and thousands separators are supported."""

    result, status = parse_amount("1.150,00")

    assert result == "1150"

    assert status == "normalized"


def test_normalize_amount_with_currency_code():
    """Recognized currency codes are removed from the amount value."""

    result, status = parse_amount("USD 1,150.00")

    assert result == "1150"

    assert status == "normalized"


def test_normalize_negative_accounting_amount():
    """Parentheses are interpreted as negative accounting notation."""

    result, status = parse_amount("(1,150.00)")

    assert result == "-1150"

    assert status == "normalized"


def test_ambiguous_amount_requires_review():
    """A single separator followed by three digits is not guessed."""

    result, status = parse_amount("1,234")

    assert result is None

    assert status == "needs_review"


def test_invalid_amount_requires_review():
    """Malformed monetary values are rejected."""

    result, status = parse_amount("12ABC34")

    assert result is None

    assert status == "needs_review"


def test_normalize_currency_code():
    """Lowercase currency codes are converted to uppercase."""

    result, status = normalize_currency("usd")

    assert result == "USD"

    assert status == "normalized"


def test_normalize_currency_name():
    """Recognized full currency names map to ISO codes."""

    result, status = normalize_currency(
        "Pakistani Rupee"
    )

    assert result == "PKR"

    assert status == "normalized"


def test_normalize_currency_symbol():
    """Unambiguous currency symbols map to their codes."""

    result, status = normalize_currency("€")

    assert result == "EUR"

    assert status == "normalized"


def test_ambiguous_currency_symbol_requires_review():
    """The dollar symbol is not automatically assigned a currency."""

    result, status = normalize_currency("$")

    assert result is None

    assert status == "needs_review"


def test_missing_values_remain_missing():
    """Missing values remain None."""

    assert normalize_text(None) == (None, "missing")

    assert normalize_date(None) == (None, "missing")

    assert parse_amount(None) == (None, "missing")

    assert normalize_currency(None) == (None, "missing")


def test_normalize_business_fields_preserves_original_values():
    """Normalization must never overwrite the original extraction."""

    business_fields = {
        "document_type": "invoice",
        "fields": {
            "total_amount": {
                "value": "1,150.00",
                "references": [
                    {
                        "type": "page",
                        "page_number": 2,
                    }
                ],
            }
        },
    }

    normalized = normalize_business_fields(
        business_fields
    )

    # Original extracted value remains unchanged.
    assert (
        business_fields["fields"]["total_amount"]["value"]
        == "1,150.00"
    )

    # The normalized result contains both values.
    normalized_field = normalized["fields"]["total_amount"]

    assert normalized_field["value"] == "1,150.00"

    assert normalized_field["normalized_value"] == "1150"

    assert normalized_field["normalization_status"] == "normalized"


def test_normalization_preserves_source_references():
    """Original page and cell references remain available."""

    business_fields = {
        "document_type": "invoice",
        "fields": {
            "invoice_number": {
                "value": "INV-1001",
                "references": [
                    {
                        "type": "cell",
                        "worksheet_name": "Invoice",
                        "cell_reference": "B2",
                    }
                ],
            }
        },
    }

    normalized = normalize_business_fields(
        business_fields
    )

    assert normalized["fields"]["invoice_number"]["references"] == (
        business_fields["fields"]["invoice_number"]["references"]
    )


def test_missing_business_field_is_marked_missing():
    """A missing invoice value receives a missing status."""

    business_fields = {
        "document_type": "invoice",
        "fields": {
            "due_date": {
                "value": None,
                "references": [],
            }
        },
    }

    normalized = normalize_business_fields(
        business_fields
    )

    field = normalized["fields"]["due_date"]

    assert field["value"] is None

    assert field["normalized_value"] is None

    assert field["normalization_status"] == "missing"


def test_invalid_business_field_structure_is_rejected():
    """Malformed business-field structures raise a clear exception."""

    with pytest.raises(BusinessFieldNormalizationError):

        normalize_business_fields(None)


def test_missing_fields_dictionary_is_rejected():
    """The fields dictionary is required."""

    with pytest.raises(BusinessFieldNormalizationError):

        normalize_business_fields(
            {
                "document_type": "invoice"
            }
        )
