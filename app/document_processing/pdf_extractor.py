
from pathlib import Path

import pymupdf


class PDFExtractionError(Exception):
    """Raised when a PDF cannot be processed."""


def extract_pdf_text(file_path: Path) -> list[dict]:
    """
    Extract text from each page of a PDF.

    Returns page-level text while preserving page numbers.
    """

    if not file_path.is_file():
        raise PDFExtractionError("PDF file not found")

    try:
        with pymupdf.open(file_path) as pdf:

            if pdf.is_encrypted:
                raise PDFExtractionError(
                    "Encrypted PDFs are not supported"
                )

            if len(pdf) == 0:
                raise PDFExtractionError(
                    "PDF contains no pages"
                )

            extracted_pages = []

            for page_number, page in enumerate(pdf, start=1):

                page_text = page.get_text("text")

                extracted_pages.append(
                    {
                        "page_number": page_number,
                        "text": page_text.strip(),
                    }
                )

            return extracted_pages

    except PDFExtractionError:
        raise

    except Exception as exc:
        raise PDFExtractionError(
            "Unable to extract text from PDF"
        ) from exc
