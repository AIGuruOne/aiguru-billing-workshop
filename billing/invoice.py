"""Invoice totalling."""

from decimal import Decimal

from .gst import SELLER_STATE, is_interstate, split_gst
from .models import Invoice
from .money import to_paise, to_rupee


def line_gross(item) -> Decimal:
    """Quantity times unit price, before any discount or tax."""
    return to_paise(item.quantity * item.unit_price)


def line_discount(item) -> Decimal:
    """The rupee value of this line's discount."""
    return to_paise(line_gross(item) * item.discount_pct / Decimal("100"))


def compute_invoice(invoice: Invoice) -> dict:
    """Return the full tax breakdown and totals for an invoice."""
    interstate = is_interstate(SELLER_STATE, invoice.customer.state)

    gross = Decimal("0.00")
    discount = Decimal("0.00")
    cgst = Decimal("0.00")
    sgst = Decimal("0.00")
    igst = Decimal("0.00")

    for item in invoice.items:
        item_gross = line_gross(item)
        gross += item_gross
        discount += line_discount(item)

        tax = split_gst(item_gross, item.gst_rate, interstate)
        cgst += tax["cgst"]
        sgst += tax["sgst"]
        igst += tax["igst"]

    total_tax = cgst + sgst + igst
    before_rounding = to_paise(gross + total_tax - discount)
    rounded = to_rupee(before_rounding)

    return {
        "gross": to_paise(gross),
        "discount": to_paise(discount),
        "taxable_value": to_paise(gross),
        "cgst": to_paise(cgst),
        "sgst": to_paise(sgst),
        "igst": to_paise(igst),
        "total_tax": to_paise(total_tax),
        "round_off": to_paise(rounded - before_rounding),
        "grand_total": before_rounding,
    }
