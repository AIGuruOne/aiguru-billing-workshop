"""Reports built on top of invoices and payments."""

from decimal import Decimal
from typing import Dict, List

from .invoice import compute_invoice
from .models import Invoice, Payment
from .money import to_paise


def amount_paid(invoice_number: str, payments: List[Payment]) -> Decimal:
    """Total received against one invoice."""
    total = sum(
        (p.amount for p in payments if p.invoice_number == invoice_number),
        Decimal("0.00"),
    )
    return to_paise(total)


def invoice_status(invoice: Invoice, payments: List[Payment]) -> str:
    """One of: cancelled, paid, part-paid, unpaid."""
    if invoice.status == "cancelled":
        return "cancelled"

    due = compute_invoice(invoice)["grand_total"]
    paid = amount_paid(invoice.number, payments)

    if paid >= due:
        return "paid"
    if paid > Decimal("0.00"):
        return "part-paid"
    return "unpaid"


def outstanding_by_customer(
    invoices: List[Invoice], payments: List[Payment]
) -> Dict[str, Decimal]:
    """Money still owed, grouped by customer name.

    Cancelled invoices are excluded. Customers who owe nothing are not listed.
    """
    owed: Dict[str, Decimal] = {}

    for invoice in invoices:
        if invoice.status == "cancelled":
            continue

        due = compute_invoice(invoice)["grand_total"]
        paid = amount_paid(invoice.number, payments)
        balance = to_paise(due - paid)

        if balance <= Decimal("0.00"):
            continue

        owed[invoice.customer.name] = to_paise(
            owed.get(invoice.customer.name, Decimal("0.00")) + balance
        )

    return owed
