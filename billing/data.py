"""Sample customers, invoices and payments so the app can be run without a database."""

from datetime import date
from decimal import Decimal

from .models import Customer, Invoice, LineItem, Payment

ACME = Customer(name="Acme Traders", gstin="24AAACA1234A1Z5", state="Gujarat")
NOVA = Customer(name="Nova Systems", gstin="27AAACN5678B1Z9", state="Maharashtra")

# Same state as Acme. Whoever created this record typed the state in lower case.
SHAH = Customer(name="Shah Enterprise", gstin="24AAACS9999C1Z1", state="gujarat")

CUSTOMERS = [ACME, NOVA, SHAH]

INVOICES = [
    Invoice(
        number="INV-001",
        issued_on=date(2026, 4, 12),
        customer=ACME,
        items=[
            LineItem("Annual maintenance contract", "998719", 2, "1500.00", 18),
        ],
    ),
    Invoice(
        number="INV-002",
        issued_on=date(2026, 4, 18),
        customer=NOVA,
        items=[
            LineItem("Control panel assembly", "853710", 3, "999.00", 12),
        ],
    ),
    Invoice(
        number="INV-003",
        issued_on=date(2026, 4, 21),
        customer=ACME,
        items=[
            LineItem("Site survey", "998346", 1, "5000.00", 18),
        ],
        status="cancelled",
    ),
    Invoice(
        number="INV-004",
        issued_on=date(2026, 5, 2),
        customer=SHAH,
        items=[
            LineItem("Bulk consumables", "391910", 1, "10000.00", 18, discount_pct=10),
        ],
    ),
]

PAYMENTS = [
    Payment(invoice_number="INV-001", received_on=date(2026, 4, 30), amount="2000.00"),
]
