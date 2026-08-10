"""Run every check in this project using nothing but the standard library.

    python check.py        (or: python3 check.py)

You do not need pytest, pip, or an internet connection.
If you already have pytest, `python -m pytest -q` runs the same checks.
"""

import sys
import traceback
from datetime import date
from decimal import Decimal

from billing.gst import is_interstate, split_gst, state_code
from billing.invoice import compute_invoice
from billing.models import Customer, Invoice, LineItem, Payment
from billing.reports import amount_paid, invoice_status, outstanding_by_customer

GUJARAT = Customer("Acme Traders", "24AAACA1234A1Z5", "Gujarat")
MAHARASHTRA = Customer("Nova Systems", "27AAACN5678B1Z9", "Maharashtra")

_checks = []


def check(name):
    def wrap(fn):
        _checks.append((name, fn))
        return fn
    return wrap


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


def acme_invoice(number, status="issued"):
    return Invoice(
        number=number,
        issued_on=date(2026, 4, 12),
        customer=GUJARAT,
        items=[LineItem("Annual maintenance contract", "998719", 2, "1500.00", 18)],
        status=status,
    )


# ---------------------------------------------------------------- GST


@check("state code is the first two digits of the GSTIN")
def _():
    assert state_code("24AAACA1234A1Z5") == "24"
    assert state_code("27AAACN5678B1Z9") == "27"


@check("same state splits into CGST and SGST")
def _():
    tax = split_gst(Decimal("1000.00"), Decimal("18"), interstate=False)
    assert tax["cgst"] == Decimal("90.00")
    assert tax["sgst"] == Decimal("90.00")
    assert tax["igst"] == Decimal("0.00")


@check("other state charges IGST only")
def _():
    tax = split_gst(Decimal("1000.00"), Decimal("18"), interstate=True)
    assert tax["cgst"] == Decimal("0.00")
    assert tax["sgst"] == Decimal("0.00")
    assert tax["igst"] == Decimal("180.00")


@check("odd paise split does not lose money")
def _():
    tax = split_gst(Decimal("333.33"), Decimal("5"), interstate=False)
    assert tax["cgst"] + tax["sgst"] == Decimal("16.67")


@check("customer in the seller state is intra-state")
def _():
    assert is_interstate("Gujarat", "Gujarat") is False


@check("customer in another state is inter-state")
def _():
    assert is_interstate("Gujarat", "Maharashtra") is True


# ------------------------------------------------------------ INVOICE


@check("intra-state invoice splits tax in half")
def _():
    totals = compute_invoice(intrastate_invoice())
    assert totals["gross"] == Decimal("3000.00")
    assert totals["cgst"] == Decimal("270.00")
    assert totals["sgst"] == Decimal("270.00")
    assert totals["igst"] == Decimal("0.00")


@check("intra-state invoice grand total")
def _():
    totals = compute_invoice(intrastate_invoice())
    assert totals["grand_total"] == Decimal("3540.00")


@check("inter-state invoice charges IGST")
def _():
    totals = compute_invoice(interstate_invoice())
    assert totals["cgst"] == Decimal("0.00")
    assert totals["sgst"] == Decimal("0.00")
    assert totals["igst"] == Decimal("359.64")


@check("round off is reported")
def _():
    totals = compute_invoice(interstate_invoice())
    assert totals["round_off"] == Decimal("0.36")


@check("grand total is rounded to the nearest rupee")
def _():
    totals = compute_invoice(interstate_invoice())
    assert totals["grand_total"] == Decimal("3357.00")


# ------------------------------------------------------------ REPORTS


@check("amount paid adds up every payment")
def _():
    payments = [
        Payment("INV-001", date(2026, 4, 30), "1200.00"),
        Payment("INV-001", date(2026, 5, 6), "800.00"),
        Payment("INV-009", date(2026, 5, 6), "500.00"),
    ]
    assert amount_paid("INV-001", payments) == Decimal("2000.00")


@check("partial payment leaves a balance")
def _():
    payments = [Payment("INV-001", date(2026, 4, 30), "2000.00")]
    owed = outstanding_by_customer([acme_invoice("INV-001")], payments)
    assert owed["Acme Traders"] == Decimal("1540.00")


@check("fully paid invoice is not listed")
def _():
    payments = [Payment("INV-001", date(2026, 4, 30), "3540.00")]
    assert outstanding_by_customer([acme_invoice("INV-001")], payments) == {}


@check("cancelled invoice is excluded")
def _():
    assert outstanding_by_customer([acme_invoice("INV-003", status="cancelled")], []) == {}


@check("invoice status reports part-paid")
def _():
    payments = [Payment("INV-001", date(2026, 4, 30), "2000.00")]
    assert invoice_status(acme_invoice("INV-001"), payments) == "part-paid"


# --------------------------------------------------------------- MAIN


def main():
    passed, failed = 0, []

    for name, fn in _checks:
        try:
            fn()
            passed += 1
            print(f"  PASS   {name}")
        except AssertionError:
            failed.append((name, traceback.format_exc(limit=2)))
            print(f"  FAIL   {name}")

    print()
    print("-" * 64)
    print(f"  {passed} passed, {len(failed)} failed, {len(_checks)} total")
    print("-" * 64)

    if failed:
        print()
        for name, tb in failed:
            print(f"FAILED: {name}")
            print(tb)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
