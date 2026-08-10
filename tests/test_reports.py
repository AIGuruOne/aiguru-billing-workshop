"""Tests for the outstanding report."""

from datetime import date
from decimal import Decimal

from billing.models import Customer, Invoice, LineItem, Payment
from billing.reports import amount_paid, invoice_status, outstanding_by_customer

ACME = Customer("Acme Traders", "24AAACA1234A1Z5", "Gujarat")


def invoice(number, status="issued"):
    return Invoice(
        number=number,
        issued_on=date(2026, 4, 12),
        customer=ACME,
        items=[LineItem("Annual maintenance contract", "998719", 2, "1500.00", 18)],
        status=status,
    )


def test_amount_paid_adds_up_every_payment():
    payments = [
        Payment("INV-001", date(2026, 4, 30), "1200.00"),
        Payment("INV-001", date(2026, 5, 6), "800.00"),
        Payment("INV-009", date(2026, 5, 6), "500.00"),
    ]
    assert amount_paid("INV-001", payments) == Decimal("2000.00")


def test_partial_payment_leaves_a_balance():
    payments = [Payment("INV-001", date(2026, 4, 30), "2000.00")]
    owed = outstanding_by_customer([invoice("INV-001")], payments)
    assert owed["Acme Traders"] == Decimal("1540.00")


def test_fully_paid_invoice_is_not_listed():
    payments = [Payment("INV-001", date(2026, 4, 30), "3540.00")]
    owed = outstanding_by_customer([invoice("INV-001")], payments)
    assert owed == {}


def test_cancelled_invoice_is_excluded():
    owed = outstanding_by_customer([invoice("INV-003", status="cancelled")], [])
    assert owed == {}


def test_invoice_status_reports_part_paid():
    payments = [Payment("INV-001", date(2026, 4, 30), "2000.00")]
    assert invoice_status(invoice("INV-001"), payments) == "part-paid"
