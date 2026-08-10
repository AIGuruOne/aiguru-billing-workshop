"""Print every sample invoice with its tax breakdown.

Run with:  python3 run_demo.py
"""

from billing.data import INVOICES, PAYMENTS
from billing.invoice import compute_invoice
from billing.reports import invoice_status, outstanding_by_customer


def rupees(value):
    return f"{value:>12,.2f}"


for invoice in INVOICES:
    totals = compute_invoice(invoice)
    print("=" * 62)
    print(f"{invoice.number}   {invoice.customer.name}   ({invoice.customer.state})")
    print(f"status: {invoice_status(invoice, PAYMENTS)}")
    print("-" * 62)
    for item in invoice.items:
        print(f"  {item.description[:34]:<34} {item.quantity:>4} x {item.unit_price:>9,.2f}")
    print("-" * 62)
    print(f"  Gross                              {rupees(totals['gross'])}")
    print(f"  Discount                           {rupees(totals['discount'])}")
    print(f"  Taxable value                      {rupees(totals['taxable_value'])}")
    print(f"  CGST                               {rupees(totals['cgst'])}")
    print(f"  SGST                               {rupees(totals['sgst'])}")
    print(f"  IGST                               {rupees(totals['igst'])}")
    print(f"  Round off                          {rupees(totals['round_off'])}")
    print(f"  GRAND TOTAL                        {rupees(totals['grand_total'])}")

print()
print("=" * 62)
print("OUTSTANDING BY CUSTOMER")
print("=" * 62)
for name, amount in outstanding_by_customer(INVOICES, PAYMENTS).items():
    print(f"  {name:<30} {rupees(amount)}")
