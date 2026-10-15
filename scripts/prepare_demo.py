"""Create invented company records and readable synthetic PDFs; no FATURA labels are used."""
import csv

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas

from billvision.config import ROOT
from billvision.db import connection, initialize


def invoice(path, invoice_number, total):
    if path.exists():
        return
    c = Canvas(str(path), pagesize=A4, invariant=1)
    c.setTitle("Completely synthetic local demo invoice")
    c.setFont("Helvetica-Bold", 23)
    c.drawString(48, 784, "INVOICE")
    c.setFont("Helvetica", 12)
    lines = [
        "SYNTHETIC DEMO - NOT A REAL COMMERCIAL DOCUMENT",
        "Supplier: Synthetic Office Supplies Pty Ltd",
        "Supplier tax ID: DEMO-TAX-001",
        f"Invoice number: {invoice_number}",
        "Invoice date: 2026-10-14",
        "Purchase order: PO-2026-001",
        "Currency: AUD",
        "Customer: Example Demo Company",
        "Description: Synthetic office supply order",
        f"Subtotal: {int(total) - 200}.00 AUD",
        "Tax total: 200.00 AUD",
        f"Total including tax: {total}.00 AUD",
        "All amounts and company relationships are invented for this demo.",
    ]
    for index, line in enumerate(lines):
        c.drawString(48, 742 - index * 38, line)
    c.save()


def main():
    initialize()
    with connection() as conn:
        with (ROOT / "data/suppliers.csv").open() as f:
            for r in csv.DictReader(f):
                conn.execute("INSERT INTO suppliers(id,name,tax_id) VALUES(%s,%s,%s) ON CONFLICT(id) DO NOTHING", (r["id"], r["name"], r["tax_id"]))
        with (ROOT / "data/purchase_orders.csv").open() as f:
            for r in csv.DictReader(f):
                conn.execute("INSERT INTO purchase_orders(id,po_number,supplier_id,currency,total,tax_basis) VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(id) DO NOTHING", tuple(r[k] for k in ["id", "po_number", "supplier_id", "currency", "total", "tax_basis"]))
    destination = ROOT / "data/demo"
    destination.mkdir(exist_ok=True)
    invoice(destination / "A-exact.pdf", "DEMO-INVOICE-A", "2000")
    invoice(destination / "B-difference.pdf", "DEMO-INVOICE-B", "2200")
    print("Synthetic company and A/B PDFs prepared. C reuses A's identical bytes. Existing records preserved.")


if __name__ == "__main__":
    main()
