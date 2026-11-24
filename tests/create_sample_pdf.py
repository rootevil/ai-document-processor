
import pymupdf


def create_sample_pdf(file_path):
    pdf = pymupdf.open()

    page1 = pdf.new_page()

    page1.insert_text(
        (72, 72),
        "INVOICE",
        fontsize=20,
    )

    page1.insert_text(
        (72, 110),
        "Invoice Number: INV-1001",
        fontsize=12,
    )

    page1.insert_text(
        (72, 140),
        "Invoice Date: 2026-11-24",
        fontsize=12,
    )

    page2 = pdf.new_page()

    page2.insert_text(
        (72, 72),
        "Invoice Details",
        fontsize=20,
    )

    page2.insert_text(
        (72, 110),
        "Subtotal: 1000",
        fontsize=12,
    )

    page2.insert_text(
        (72, 140),
        "Total: 1150",
        fontsize=12,
    )

    pdf.save(file_path)

    pdf.close()
