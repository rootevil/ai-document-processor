
"""
Business-field extraction module.

Responsibilities:
1. Identify invoice documents.
2. Extract invoice fields from PDF documents.
3. Extract invoice fields from Excel workbooks.
4. Preserve references to the original source locations.
5. Represent missing fields as None rather than guessing.
6. Provide an extensible structure for future document types.

This module does not replace PDF or Excel extraction.

It works with the unified extraction result produced
by document_processor.py.
"""

import re


class BusinessFieldExtractionError(Exception):
    """
    Raised when business-field extraction cannot be performed.

    This exception represents problems with the input
    extraction structure or unsupported document formats.
    """


# Centralized list of fields supported by the initial
# invoice extraction implementation.
#
# Keeping this list in one place makes it easier to add
# more fields and future document types.
INVOICE_FIELDS = [
    "invoice_number",
    "invoice_date",
    "due_date",
    "vendor_name",
    "customer_name",
    "subtotal",
    "tax_amount",
    "total_amount",
    "currency",
]


# PDF field patterns.
#
# Each pattern matches a field label at the beginning
# of a line, followed by its extracted value.
#
# Anchoring patterns to the beginning of a line prevents
# "Subtotal" from accidentally matching "Total".
PDF_FIELD_PATTERNS = {
    "invoice_number": re.compile(
        r"^\s*(?:invoice\s+(?:number|no\.?|id)|invoice\s*#)"
        r"\s*[:#-]\s*(.*?)\s*$",
        re.IGNORECASE,
    ),

    "invoice_date": re.compile(
        r"^\s*(?:invoice\s+date|date\s+of\s+issue|issue\s+date|"
        r"date\s+issued|issued\s+on)"
        r"\s*[:\-]\s*(.*?)\s*$",
        re.IGNORECASE,
    ),

    "due_date": re.compile(
        r"^\s*(?:due\s+date|payment\s+due)"
        r"\s*[:\-]\s*(.*?)\s*$",
        re.IGNORECASE,
    ),

    "vendor_name": re.compile(
        r"^\s*(?:vendor(?:\s+name)?|supplier(?:\s+name)?|"
        r"seller(?:\s+name)?|from|billed\s+by|sold\s+by|issued\s+by|"
        r"provided\s+by)"
        r"\s*[:\-]\s*(.*?)\s*$",
        re.IGNORECASE,
    ),

    "customer_name": re.compile(
        r"^\s*(?:customer(?:\s+name)?|client(?:\s+name)?|"
        r"bill(?:ed)?\s+to|sold\s+to)"
        r"\s*[:\-]\s*(.*?)\s*$",
        re.IGNORECASE,
    ),

    "subtotal": re.compile(
        r"^\s*(?:sub\s*total|subtotal)"
        r"\s*[:\-]\s*(.*?)\s*$",
        re.IGNORECASE,
    ),

    "tax_amount": re.compile(
        r"^\s*(?:tax(?:\s+amount)?|vat|gst|sales\s+tax|"
        r"goods\s+and\s+services\s+tax)"
        r"\s*[:\-]\s*(.*?)\s*$",
        re.IGNORECASE,
    ),

    "total_amount": re.compile(
        r"^\s*(?:grand\s+total|invoice\s+total|total\s+amount|"
        r"amount\s+due|total\s+due|total\s+payable|amount\s+payable|total)"
        r"\s*[:\-]\s*(.*?)\s*$",
        re.IGNORECASE,
    ),

    "currency": re.compile(
        r"^\s*currency\s*[:\-]\s*(.*?)\s*$",
        re.IGNORECASE,
    ),
}


# PDF text extraction often places a recognized label on one line and
# its value on the next. These exact normalized labels let us support
# that layout without treating unrelated lines such as "Date paid" as
# an invoice date.
PDF_LABEL_TO_FIELD = {
    "invoice number": "invoice_number",
    "invoice no": "invoice_number",
    "invoice id": "invoice_number",
    "invoice date": "invoice_date",
    "date of issue": "invoice_date",
    "issue date": "invoice_date",
    "date issued": "invoice_date",
    "issued on": "invoice_date",
    "due date": "due_date",
    "payment due": "due_date",
    "vendor": "vendor_name",
    "vendor name": "vendor_name",
    "supplier": "vendor_name",
    "supplier name": "vendor_name",
    "seller": "vendor_name",
    "seller name": "vendor_name",
    "from": "vendor_name",
    "billed by": "vendor_name",
    "sold by": "vendor_name",
    "issued by": "vendor_name",
    "provided by": "vendor_name",
    "customer": "customer_name",
    "customer name": "customer_name",
    "client": "customer_name",
    "client name": "customer_name",
    "bill to": "customer_name",
    "billed to": "customer_name",
    "sold to": "customer_name",
    "subtotal": "subtotal",
    "sub total": "subtotal",
    "tax": "tax_amount",
    "tax amount": "tax_amount",
    "vat": "tax_amount",
    "gst": "tax_amount",
    "sales tax": "tax_amount",
    "goods and services tax": "tax_amount",
    "total": "total_amount",
    "grand total": "total_amount",
    "invoice total": "total_amount",
    "total amount": "total_amount",
    "amount due": "total_amount",
    "total due": "total_amount",
    "total payable": "total_amount",
    "amount payable": "total_amount",
    "currency": "currency",
}


# Excel uses individual cells instead of continuous text.
#
# These normalized labels map spreadsheet labels
# to our standard invoice-field names.
EXCEL_LABEL_TO_FIELD = {
    "invoice number": "invoice_number",
    "invoice no": "invoice_number",
    "invoice id": "invoice_number",

    "invoice date": "invoice_date",
    "date of issue": "invoice_date",
    "issue date": "invoice_date",

    "due date": "due_date",
    "payment due": "due_date",

    "vendor": "vendor_name",
    "vendor name": "vendor_name",
    "supplier": "vendor_name",
    "supplier name": "vendor_name",
    "seller": "vendor_name",
    "seller name": "vendor_name",

    "customer": "customer_name",
    "customer name": "customer_name",
    "client": "customer_name",
    "client name": "customer_name",
    "bill to": "customer_name",

    "subtotal": "subtotal",
    "sub total": "subtotal",

    "tax": "tax_amount",
    "tax amount": "tax_amount",
    "vat": "tax_amount",
    "sales tax": "tax_amount",

    "total": "total_amount",
    "grand total": "total_amount",
    "invoice total": "total_amount",
    "total amount": "total_amount",
    "amount due": "total_amount",

    "currency": "currency",
}


def create_empty_invoice_fields() -> dict:
    """
    Create a standard invoice-field structure.

    Every field starts with:
    - value: None
    - references: an empty list

    Extraction functions populate these values when
    matching information is found.
    """

    return {
        field_name: {
            "value": None,
            "references": [],
        }
        for field_name in INVOICE_FIELDS
    }


def normalize_field_label(value: str) -> str:
    """
    Normalize a field label for consistent matching.

    Examples:
        "Invoice Number:" -> "invoice number"
        "Customer Name"   -> "customer name"
        "Grand-Total"     -> "grand total"

    This helps Excel extraction match labels despite
    differences in capitalization and punctuation.
    """

    normalized = re.sub(
        r"[^a-z0-9]+",
        " ",
        str(value).lower(),
    )

    return normalized.strip()


def set_extracted_field(
    fields: dict,
    field_name: str,
    value,
    reference: dict,
) -> None:
    """
    Save an extracted field and its source reference.

    A field is only populated when:
    1. A non-empty value exists.
    2. The field has not already been populated.

    This prevents later duplicate matches from
    accidentally overwriting the first extracted value.
    """

    if value is None:
        return

    if isinstance(value, str):
        value = value.strip()

    if value == "":
        return

    if fields[field_name]["value"] is not None:
        return

    fields[field_name]["value"] = value

    fields[field_name]["references"] = [
        reference
    ]


def get_page_number(section: dict):
    """
    Retrieve the original PDF page number.

    The unified extraction structure stores page
    references separately from page content.

    The section name is used as a fallback.
    """

    for reference in section.get("references", []):

        if (
            isinstance(reference, dict)
            and reference.get("type") == "page"
        ):
            return reference.get("page_number")

    try:
        return int(section.get("section_name"))

    except (TypeError, ValueError):
        return None


BUSINESS_NAME_SUFFIX = re.compile(
    r"(?:\b(?:incorporated|inc\.?|llc|l\.l\.c\.|limited|ltd\.?|"
    r"corporation|corp\.?|gmbh|plc|llp|l\.l\.p\.|"
    r"pty\s+ltd\.?|company|co\.)\s*)$",
    re.IGNORECASE,
)

CURRENCY_CODES = "USD|EUR|GBP|PKR|INR|AED|CAD|AUD|JPY|CNY|CHF"
CURRENCY_SYMBOLS = "$€£¥₹₨"


def infer_header_vendor_name(lines: list[str]) -> str | None:
    """Use a narrow legal-suffix rule for an unlabeled issuer header.

    Only scan before the first buyer label and only accept recognizable
    legal entity suffixes. This avoids treating arbitrary document text
    or the customer block as the vendor.
    """

    buyer_labels = {
        field_label
        for field_label, field_name in PDF_LABEL_TO_FIELD.items()
        if field_name == "customer_name"
    }

    buyer_start = next(
        (
            index
            for index, line in enumerate(lines)
            if normalize_field_label(line) in buyer_labels
        ),
        len(lines),
    )

    for line in lines[:buyer_start]:
        candidate = line.strip()
        if BUSINESS_NAME_SUFFIX.search(candidate):
            return candidate

    return None


def extract_currency_marker(line: str) -> str | None:
    """Return an explicit currency code or symbol attached to an amount.

    Dollar, yen, and rupee symbols remain symbols because they can map to
    multiple currencies; the normalizer marks those values for review.
    """

    code_before_amount = re.search(
        rf"\b(?P<code>{CURRENCY_CODES})\b"
        rf"(?:\s+|[{re.escape(CURRENCY_SYMBOLS)}]\s*)[-+]?\d",
        line,
        re.IGNORECASE,
    )
    if code_before_amount:
        return code_before_amount.group("code").upper()

    code_after_amount = re.search(
        rf"[-+]?\d[\d.,]*\s+(?P<code>{CURRENCY_CODES})\b",
        line,
        re.IGNORECASE,
    )
    if code_after_amount:
        return code_after_amount.group("code").upper()

    symbol_before_amount = re.search(
        rf"(?P<symbol>[{re.escape(CURRENCY_SYMBOLS)}])\s*[-+]?\d",
        line,
    )
    if symbol_before_amount:
        return symbol_before_amount.group("symbol")

    symbol_after_amount = re.search(
        rf"[-+]?\d[\d.,]*\s*(?P<symbol>[{re.escape(CURRENCY_SYMBOLS)}])",
        line,
    )
    if symbol_after_amount:
        return symbol_after_amount.group("symbol")

    return None


def extract_pdf_invoice_fields(sections: list[dict]) -> dict:
    """
    Extract invoice fields from PDF page sections.

    Each extracted field keeps a reference to the page
    containing its original value.

    The original PDF extraction result is not modified.
    """

    fields = create_empty_invoice_fields()
    currency_candidates = {}

    for section in sections:

        # Ignore sections that are not PDF pages.
        if not isinstance(section, dict):
            continue

        if section.get("section_type") != "page":
            continue

        # Retrieve the text extracted from the current page.
        content = section.get("content", {})

        if not isinstance(content, dict):
            continue

        page_text = content.get("text", "")

        if not isinstance(page_text, str):
            continue

        # Determine the original page number.
        page_number = get_page_number(section)

        if page_number is None:
            continue

        # Process the page line by line. Keep the original lines so
        # label/value pairs on separate lines can retain page references.
        lines = page_text.splitlines()

        for line_index, line in enumerate(lines):

            currency_marker = extract_currency_marker(line)
            if currency_marker is not None:
                currency_candidates.setdefault(
                    currency_marker,
                    {
                        "type": "page",
                        "page_number": page_number,
                    },
                )

            # Check every supported invoice field.
            for field_name, pattern in PDF_FIELD_PATTERNS.items():

                match = pattern.match(line)

                if not match:
                    continue

                extracted_value = match.group(1).strip()

                # Preserve the source page for traceability.
                reference = {
                    "type": "page",
                    "page_number": page_number,
                }

                set_extracted_field(
                    fields=fields,
                    field_name=field_name,
                    value=extracted_value,
                    reference=reference,
                )

            # Some PDFs put a bare field label on one line and its value
            # on the next (for example, "Invoice number" then "INV-1001").
            normalized_label = normalize_field_label(line)
            field_name = PDF_LABEL_TO_FIELD.get(normalized_label)

            if field_name is None or fields[field_name]["value"] is not None:
                continue

            next_index = line_index + 1
            while next_index < len(lines) and not lines[next_index].strip():
                next_index += 1

            if next_index >= len(lines):
                continue

            next_line = lines[next_index].strip()

            # Don't consume another recognized label as this field's value.
            if normalize_field_label(next_line) in PDF_LABEL_TO_FIELD:
                continue

            reference = {
                "type": "page",
                "page_number": page_number,
            }

            set_extracted_field(
                fields=fields,
                field_name=field_name,
                value=next_line,
                reference=reference,
            )

        # Many invoices show the issuer as a company name in the header
        # without a "Vendor" label. Use a conservative legal-suffix rule.
        if fields["vendor_name"]["value"] is None:
            vendor_name = infer_header_vendor_name(lines)
            if vendor_name is not None:
                set_extracted_field(
                    fields=fields,
                    field_name="vendor_name",
                    value=vendor_name,
                    reference={
                        "type": "page",
                        "page_number": page_number,
                    },
                )

    # Keep a currency marker only when the document contains one
    # consistent marker. Ambiguous symbols are preserved for review.
    if fields["currency"]["value"] is None and len(currency_candidates) == 1:
        currency_marker, reference = next(iter(currency_candidates.items()))
        set_extracted_field(
            fields=fields,
            field_name="currency",
            value=currency_marker,
            reference=reference,
        )

    return fields


def is_formula_cell(cell: dict) -> bool:
    """
    Determine whether an Excel cell contains a formula.

    The existing Excel extractor preserves formulas and
    marks their data_type as "f".

    We skip formulas because the current extractor does
    not calculate formula results.

    This prevents formula strings from being mistaken
    for actual invoice amounts.
    """

    if cell.get("data_type") == "f":
        return True

    value = cell.get("value")

    if isinstance(value, str) and value.startswith("="):
        return True

    return False


def extract_excel_invoice_fields(sections: list[dict]) -> dict:
    """
    Extract invoice fields from Excel worksheet sections.

    The initial implementation expects the field label
    in one cell and its value in the immediately adjacent
    cell to the right.

    Example:
        A2 = Invoice Number
        B2 = INV-1001

    The reference points to B2, where the value was found.
    """

    fields = create_empty_invoice_fields()

    for section in sections:

        # Only process worksheet sections.
        if not isinstance(section, dict):
            continue

        if section.get("section_type") != "worksheet":
            continue

        worksheet_name = section.get("section_name", "")

        content = section.get("content", {})

        if not isinstance(content, dict):
            continue

        rows = content.get("rows", [])

        if not isinstance(rows, list):
            continue

        # Build a lookup table using row and column numbers.
        #
        # This allows us to locate the cell immediately
        # to the right of each recognized field label.
        cell_lookup = {}

        for row in rows:

            if not isinstance(row, dict):
                continue

            cells = row.get("cells", [])

            for cell in cells:

                if not isinstance(cell, dict):
                    continue

                row_number = cell.get("row_number")
                column_number = cell.get("column_number")

                if row_number is None or column_number is None:
                    continue

                cell_lookup[
                    (row_number, column_number)
                ] = cell

        # Examine each cell to find recognized field labels.
        for (row_number, column_number), label_cell in cell_lookup.items():

            # Formula cells must not be treated as field labels.
            if is_formula_cell(label_cell):
                continue

            label_value = label_cell.get("value")

            if not isinstance(label_value, str):
                continue

            normalized_label = normalize_field_label(label_value)

            field_name = EXCEL_LABEL_TO_FIELD.get(
                normalized_label
            )

            if field_name is None:
                continue

            # Find the value in the immediately adjacent cell.
            value_cell = cell_lookup.get(
                (row_number, column_number + 1)
            )

            if value_cell is None:
                continue

            # Ignore formula results because they have not
            # been calculated by our existing extractor.
            if is_formula_cell(value_cell):
                continue

            extracted_value = value_cell.get("value")

            # Preserve the exact worksheet and cell location.
            reference = {
                "type": "cell",
                "worksheet_name": worksheet_name,
                "cell_reference": value_cell.get("cell_reference"),
            }

            set_extracted_field(
                fields=fields,
                field_name=field_name,
                value=extracted_value,
                reference=reference,
            )

    return fields


def document_contains_invoice_marker(
    extraction_result: dict,
) -> bool:
    """
    Determine whether the source contains invoice indicators.

    PDF:
        Search extracted page text for the word "invoice".

    Excel:
        Search worksheet names and cell values for invoice
        indicators.

    This is a basic rule-based classification mechanism.
    More advanced document classification can be added later.
    """

    file_type = extraction_result.get("file_type")

    sections = extraction_result.get("sections", [])

    for section in sections:

        if not isinstance(section, dict):
            continue

        # Check PDF page text.
        if file_type == "pdf":

            content = section.get("content", {})

            if not isinstance(content, dict):
                continue

            page_text = content.get("text", "")

            if re.search(
                r"\binvoice\b",
                str(page_text),
                re.IGNORECASE,
            ):
                return True

        # Check Excel worksheet names and cell values.
        elif file_type == "xlsx":

            worksheet_name = section.get("section_name", "")

            if re.search(
                r"\binvoice\b",
                str(worksheet_name),
                re.IGNORECASE,
            ):
                return True

            content = section.get("content", {})

            if not isinstance(content, dict):
                continue

            for row in content.get("rows", []):

                if not isinstance(row, dict):
                    continue

                for cell in row.get("cells", []):

                    if not isinstance(cell, dict):
                        continue

                    if re.search(
                        r"\binvoice\b",
                        str(cell.get("value", "")),
                        re.IGNORECASE,
                    ):
                        return True

    return False


def extract_invoice_fields(extraction_result: dict) -> dict:
    """
    Public entry point for invoice business-field extraction.

    This function selects the appropriate extraction method
    based on the original document format.

    Supported formats:
        - PDF
        - XLSX

    Returns:
        {
            "document_type": "invoice",
            "fields": {
                ...
            }
        }

    Unsupported formats and invalid input structures
    raise BusinessFieldExtractionError.
    """

    # Validate the input before attempting extraction.
    if not isinstance(extraction_result, dict):
        raise BusinessFieldExtractionError(
            "Extraction result must be a dictionary"
        )

    file_type = extraction_result.get("file_type")

    sections = extraction_result.get("sections")

    if not isinstance(sections, list):
        raise BusinessFieldExtractionError(
            "Extraction result must contain a sections list"
        )

    # Select the correct extraction implementation.
    if file_type == "pdf":

        fields = extract_pdf_invoice_fields(sections)

    elif file_type == "xlsx":

        fields = extract_excel_invoice_fields(sections)

    else:

        raise BusinessFieldExtractionError(
            f"Unsupported file type for invoice extraction: {file_type}"
        )

    # Classify the source using the available invoice indicators.
    is_invoice = document_contains_invoice_marker(
        extraction_result
    )

    return {
        "document_type": "invoice" if is_invoice else "unknown",
        "fields": fields,
    }
