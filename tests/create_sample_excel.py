
from openpyxl import Workbook


def create_sample_excel(file_path):

    workbook = Workbook()

    # First worksheet: Invoice
    worksheet = workbook.active
    worksheet.title = "Invoice"

    worksheet.merge_cells("A1:C1")
    worksheet["A1"] = "INVOICE"

    worksheet["A2"] = "Invoice Number"
    worksheet["B2"] = "INV-1001"

    worksheet["A3"] = "Invoice Date"
    worksheet["B3"] = "2026-11-24"

    worksheet["A5"] = "Description"
    worksheet["B5"] = "Quantity"
    worksheet["C5"] = "Unit Price"

    worksheet["A6"] = "Laptop"
    worksheet["B6"] = 2
    worksheet["C6"] = 1000

    worksheet["A7"] = "Mouse"
    worksheet["B7"] = 5
    worksheet["C7"] = 20

    worksheet["D8"] = "=SUM(B6:B7)"

    # Second worksheet: Customer Details
    customer_sheet = workbook.create_sheet(
        title="Customer Details"
    )

    customer_sheet["A1"] = "Customer Name"
    customer_sheet["B1"] = "ABC Technologies"

    customer_sheet["A2"] = "Email"
    customer_sheet["B2"] = "billing@example.com"

    workbook.save(file_path)

    workbook.close()
