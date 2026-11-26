
"""
Business-value normalization module.

Responsibilities:
1. Normalize extracted invoice dates.
2. Normalize monetary amounts safely using Decimal.
3. Normalize recognized currency codes and names.
4. Clean extracted names and text values.
5. Preserve every original extracted value.
6. Preserve source references from PDF and Excel documents.
7. Identify ambiguous values that require human review.

This module does not perform document extraction.

It receives the business-field structure produced by
business_field_extractor.py and creates a normalized copy.
"""

import re

from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal, InvalidOperation


class BusinessFieldNormalizationError(Exception):
    """Raised when business-field normalization cannot be performed."""


# Fields containing dates.
DATE_FIELDS = {
    "invoice_date",
    "due_date",
}


# Fields containing monetary amounts.
AMOUNT_FIELDS = {
    "subtotal",
    "tax_amount",
    "total_amount",
}


# Fields containing names or identifiers.
TEXT_FIELDS = {
    "invoice_number",
    "vendor_name",
    "customer_name",
}


# Explicit currency names and codes.
#
# Ambiguous currency symbols are deliberately not included.
# For example, "$" can represent multiple currencies.
CURRENCY_ALIASES = {
    "USD": "USD",
    "US DOLLAR": "USD",
    "US DOLLARS": "USD",
    "UNITED STATES DOLLAR": "USD",

    "EUR": "EUR",
    "EURO": "EUR",

    "GBP": "GBP",
    "BRITISH POUND": "GBP",
    "POUND STERLING": "GBP",

    "PKR": "PKR",
    "PAKISTANI RUPEE": "PKR",

    "INR": "INR",
    "INDIAN RUPEE": "INR",

    "AED": "AED",
    "UAE DIRHAM": "AED",

    "CAD": "CAD",
    "CANADIAN DOLLAR": "CAD",

    "AUD": "AUD",
    "AUSTRALIAN DOLLAR": "AUD",

    "JPY": "JPY",
    "JAPANESE YEN": "JPY",

    "CNY": "CNY",
    "CHINESE YUAN": "CNY",

    "CHF": "CHF",
    "SWISS FRANC": "CHF",
}


# Currency symbols that uniquely identify a currency
# within this initial supported mapping.
UNAMBIGUOUS_CURRENCY_SYMBOLS = {
    "€": "EUR",
    "£": "GBP",
    "₹": "INR",
}


SUPPORTED_CURRENCY_CODES = set(CURRENCY_ALIASES.values())


def normalize_text(value) -> tuple:
    """
    Normalize names and identifiers.

    Examples:
        "  ABC Technologies  " -> "ABC Technologies"
        "INV- 1001"             -> "INV- 1001"

    Internal whitespace is collapsed to a single space.

    Original capitalization and punctuation are preserved.
    """

    if value is None:
        return None, "missing"

    normalized = re.sub(
        r"\s+",
        " ",
        str(value),
    ).strip()

    if not normalized:
        return None, "missing"

    return normalized, "normalized"


def normalize_date(value) -> tuple:
    """
    Convert a recognizable date into ISO YYYY-MM-DD format.

    Supported examples:
        2026-11-24
        2026/11/24
        24/11/2026
        11/24/2026
        24 November 2026
        November 24, 2026

    Ambiguous numeric dates are not guessed.

    Returns:
        (normalized_value, status)
    """

    if value is None:
        return None, "missing"

    # Excel may provide actual Python date objects.
    if isinstance(value, datetime):

        return value.date().isoformat(), "normalized"

    if isinstance(value, date):

        return value.isoformat(), "normalized"

    raw_value = str(value).strip()

    if not raw_value:
        return None, "missing"

    # STEP 1:
    # Try the unambiguous ISO date format.
    try:

        parsed_date = date.fromisoformat(raw_value)

        return parsed_date.isoformat(), "normalized"

    except ValueError:
        pass

    # STEP 2:
    # Handle year-first dates with slash separators.
    try:

        parsed_date = datetime.strptime(
            raw_value,
            "%Y/%m/%d",
        ).date()

        return parsed_date.isoformat(), "normalized"

    except ValueError:
        pass

    # STEP 3:
    # Handle numeric day/month/year and month/day/year.
    numeric_match = re.fullmatch(
        r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})",
        raw_value,
    )

    if numeric_match:

        first = int(numeric_match.group(1))
        second = int(numeric_match.group(2))
        year = int(numeric_match.group(3))

        # If the first number exceeds 12, the format
        # must be day/month/year.
        if first > 12:

            day_value = first
            month_value = second

        # If the second number exceeds 12, the format
        # must be month/day/year.
        elif second > 12:

            month_value = first
            day_value = second

        else:

            # Both interpretations are possible.
            # Never guess the user's intended date.
            return None, "needs_review"

        try:

            parsed_date = date(
                year,
                month_value,
                day_value,
            )

            return parsed_date.isoformat(), "normalized"

        except ValueError:

            return None, "needs_review"

    # STEP 4:
    # Handle dates containing written month names.
    supported_formats = [
        "%d %B %Y",
        "%B %d, %Y",
        "%d %b %Y",
        "%b %d, %Y",
    ]

    for date_format in supported_formats:

        try:

            parsed_date = datetime.strptime(
                raw_value,
                date_format,
            ).date()

            return parsed_date.isoformat(), "normalized"

        except ValueError:
            continue

    # The original value remains available for review.
    return None, "needs_review"


def parse_amount(value) -> tuple:
    """
    Convert a monetary value into a canonical decimal string.

    Decimal is used instead of float to avoid financial
    precision problems.

    Supported examples:
        1150
        1150.00
        1,150.00
        1.150,00
        USD 1,150.00
        €1.150,00

    Ambiguous separator formats are flagged for review.

    The returned amount does not include a currency symbol.
    Currency normalization is handled separately.
    """

    if value is None:

        return None, "missing"

    # Handle numeric values directly.
    if isinstance(value, bool):

        return None, "needs_review"

    if isinstance(value, (int, float, Decimal)):

        try:

            amount = Decimal(str(value))

        except InvalidOperation:

            return None, "needs_review"

        if not amount.is_finite():

            return None, "needs_review"

        return format(amount.normalize(), "f"), "normalized"

    raw_value = str(value).strip()

    if not raw_value:

        return None, "missing"

    # Support accounting notation for negative amounts.
    is_negative = (
        raw_value.startswith("(")
        and raw_value.endswith(")")
    )

    if is_negative:

        raw_value = raw_value[1:-1].strip()

    # Remove known ISO currency codes.
    currency_code_pattern = (
        r"\b(?:"
        + "|".join(sorted(SUPPORTED_CURRENCY_CODES))
        + r")\b"
    )

    raw_value = re.sub(
        currency_code_pattern,
        "",
        raw_value,
        flags=re.IGNORECASE,
    )

    # Remove common currency symbols.
    # This does not infer or assign a currency code.
    raw_value = re.sub(
        r"[$€£¥₹₨]",
        "",
        raw_value,
    )

    # Remove surrounding whitespace.
    raw_value = raw_value.strip()

    # Allow only numeric characters and separators.
    if not re.fullmatch(r"[+-]?[\d.,]+", raw_value):

        return None, "needs_review"

    if raw_value.count("+") + raw_value.count("-") > 1:

        return None, "needs_review"

    # STEP 1:
    # When both comma and dot appear, the last separator
    # is treated as the decimal separator.
    if "," in raw_value and "." in raw_value:

        decimal_separator = (
            ","
            if raw_value.rfind(",") > raw_value.rfind(".")
            else "."
        )

        grouping_separator = (
            "."
            if decimal_separator == ","
            else ","
        )

        integer_part, fractional_part = raw_value.rsplit(
            decimal_separator,
            1,
        )

        # Decimal fractions must contain digits.
        if not fractional_part.isdigit():

            return None, "needs_review"

        # Verify that grouping separators are correctly placed.
        integer_groups = integer_part.lstrip("+-").split(
            grouping_separator
        )

        if len(integer_groups) > 1:

            if not (
                1 <= len(integer_groups[0]) <= 3
                and all(
                    len(group) == 3 and group.isdigit()
                    for group in integer_groups[1:]
                )
            ):

                return None, "needs_review"

        integer_digits = integer_part.replace(
            grouping_separator,
            "",
        )

        normalized_string = (
            integer_digits
            + "."
            + fractional_part
        )

    # STEP 2:
    # Handle values containing only one separator type.
    elif "," in raw_value or "." in raw_value:

        separator = (
            ","
            if "," in raw_value
            else "."
        )

        parts = raw_value.split(separator)

        # Multiple separators are treated as grouping only
        # when all groups follow standard three-digit grouping.
        if len(parts) > 2:

            if not (
                1 <= len(parts[0].lstrip("+-")) <= 3
                and all(
                    len(group) == 3 and group.isdigit()
                    for group in parts[1:]
                )
            ):

                return None, "needs_review"

            normalized_string = "".join(parts)

        else:

            integer_part, fractional_part = parts

            if not fractional_part.isdigit():

                return None, "needs_review"

            # A single separator followed by three digits
            # could mean either a decimal or a thousands
            # separator. We deliberately reject that ambiguity.
            if (
                len(fractional_part) == 3
                and 1 <= len(integer_part.lstrip("+-")) <= 3
            ):

                return None, "needs_review"

            normalized_string = (
                integer_part
                + "."
                + fractional_part
            )

    else:

        normalized_string = raw_value

    try:

        amount = Decimal(normalized_string)

    except InvalidOperation:

        return None, "needs_review"

    if not amount.is_finite():

        return None, "needs_review"

    if is_negative:

        amount = -abs(amount)

    # Remove insignificant trailing zeros without
    # converting the amount into a floating-point number.
    normalized_amount = format(
        amount.normalize(),
        "f",
    )

    if normalized_amount in {"-0", "+0", ""}:

        normalized_amount = "0"

    return normalized_amount, "normalized"


def normalize_currency(value) -> tuple:
    """
    Normalize recognized currency codes and currency names.

    Examples:
        usd                  -> USD
        Pakistani Rupee      -> PKR
        Euro                 -> EUR
        €                    -> EUR

    Ambiguous symbols such as "$" and "¥" are not assigned
    a currency automatically.
    """

    if value is None:

        return None, "missing"

    raw_value = str(value).strip()

    if not raw_value:

        return None, "missing"

    # Recognize unambiguous currency symbols.
    if raw_value in UNAMBIGUOUS_CURRENCY_SYMBOLS:

        return (
            UNAMBIGUOUS_CURRENCY_SYMBOLS[raw_value],
            "normalized",
        )

    normalized_label = re.sub(
        r"\s+",
        " ",
        raw_value.upper(),
    ).strip()

    # Identify known currency codes and full names.
    currency_code = CURRENCY_ALIASES.get(
        normalized_label
    )

    if currency_code:

        return currency_code, "normalized"

    # Ambiguous currency symbols require human review.
    if raw_value in {"$", "¥", "₨"}:

        return None, "needs_review"

    return None, "needs_review"


def normalize_field_value(field_name: str, value) -> tuple:
    """
    Select the appropriate normalization rule for a field.

    Keeping field-specific behavior in one function makes
    the normalizer easier to extend when new document types
    and business fields are introduced.
    """

    if field_name in DATE_FIELDS:

        return normalize_date(value)

    if field_name in AMOUNT_FIELDS:

        return parse_amount(value)

    if field_name in TEXT_FIELDS:

        return normalize_text(value)

    if field_name == "currency":

        return normalize_currency(value)

    # Unknown fields are retained without modification.
    if value is None:

        return None, "missing"

    return value, "not_applicable"


def normalize_business_fields(business_fields: dict) -> dict:
    """
    Normalize every field in a business-field extraction result.

    The function creates a separate result and never modifies
    the original business-field extraction.

    Each field retains:
        value               Original extracted value.
        normalized_value   Standardized value.
        normalization_status
        references          Original source references.

    This makes normalized values traceable and suitable
    for future human-review workflows.
    """

    if not isinstance(business_fields, dict):

        raise BusinessFieldNormalizationError(
            "Business fields must be provided as a dictionary"
        )

    original_fields = business_fields.get("fields")

    if not isinstance(original_fields, dict):

        raise BusinessFieldNormalizationError(
            "Business fields must contain a fields dictionary"
        )

    # Create a separate result so the original extraction
    # remains unchanged.
    normalized_result = deepcopy(business_fields)

    normalized_fields = {}

    for field_name, field_data in original_fields.items():

        if not isinstance(field_data, dict):

            raise BusinessFieldNormalizationError(
                f"Invalid field structure: {field_name}"
            )

        original_value = field_data.get("value")

        # Apply the correct normalization rule.
        normalized_value, status = normalize_field_value(
            field_name,
            original_value,
        )

        # Preserve the original value and references.
        normalized_fields[field_name] = {
            "value": deepcopy(original_value),
            "normalized_value": normalized_value,
            "normalization_status": status,
            "references": deepcopy(
                field_data.get("references", [])
            ),
        }

    normalized_result["fields"] = normalized_fields

    return normalized_result
