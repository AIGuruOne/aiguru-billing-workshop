"""Tests for invoice totalling."""

from datetime import date
from decimal import Decimal

from billing.invoice import compute_invoice
from billing.models import Customer, Invoice, LineItem

GUJARAT = Customer("Acme Traders", "24AAACA1234A1Z5", "Gujarat")
MAHARASHTRA = Customer("Nova Systems", "27AAACN5678B1Z9", "Maharashtra")


def intrastate_invoice():
    return Invoice(
        number="INV-001",
        issued_on=date(2026, 4, 12),
        customer=GUJARAT,
        items=[LineItem("Annual maintenance contract", "998719", 2, "1500.00", 18)],
    )


def interstate_invoice():
    return Invoice(
        number="INV-002",
        issued_on=date(2026, 4, 18),
        customer=MAHARASHTRA,
        items=[LineItem("Control panel assembly", "853710", 3, "999.00", 12)],
    )


def test_intrastate_invoice_splits_tax_in_half():
    totals = compute_invoice(intrastate_invoice())
    assert totals["gross"] == Decimal("3000.00")
    assert totals["cgst"] == Decimal("270.00")
    assert totals["sgst"] == Decimal("270.00")
    assert totals["igst"] == Decimal("0.00")


def test_intrastate_invoice_grand_total():
    totals = compute_invoice(intrastate_invoice())
    assert totals["grand_total"] == Decimal("3540.00")


def test_interstate_invoice_charges_igst():
    totals = compute_invoice(interstate_invoice())
    assert totals["cgst"] == Decimal("0.00")
    assert totals["sgst"] == Decimal("0.00")
    assert totals["igst"] == Decimal("359.64")


def test_round_off_is_reported():
    """An invoice ending in paise must report the rounding adjustment."""
    totals = compute_invoice(interstate_invoice())
    assert totals["round_off"] == Decimal("0.36")


def test_grand_total_is_rounded_to_the_nearest_rupee():
    """Printed invoices are always a whole rupee amount."""
    totals = compute_invoice(interstate_invoice())
    assert totals["grand_total"] == Decimal("3357.00")
