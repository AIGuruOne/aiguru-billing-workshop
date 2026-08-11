"""The billing engine exposed as tools an LLM can call.

Two things live here: the JSON schemas that describe each tool to the model,
and the plain Python that answers it. They are deliberately in one file so a
schema and its implementation cannot drift apart unnoticed.

Nothing here talks to a network. The model decides *which* tool to call; the
answers still come from the same `billing` code the invoices are printed from,
so the engine remains the single source of truth and the model cannot invent a
total.
"""

from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional

from .data import INVOICES, PAYMENTS
from .gst import state_code
from .invoice import compute_invoice
from .models import Invoice
from .reports import amount_paid, invoice_status, outstanding_by_customer
from .states import UnknownState, is_known_state, normalise_state, state_abbr

PENDING = ("unpaid", "part-paid")


def _rupees(value: Decimal) -> str:
    """Render a Decimal for JSON.

    Sent as a string, not a float, so the model never sees a value that has
    already lost paise on its way through JSON.
    """
    return f"{value:.2f}"


def _describe(invoice: Invoice) -> Dict[str, Any]:
    """Flatten one invoice into the shape the model sees."""
    totals = compute_invoice(invoice)
    paid = amount_paid(invoice.number, PAYMENTS)
    due = totals["grand_total"]
    balance = due - paid

    typed_state = invoice.customer.state
    return {
        "invoice_number": invoice.number,
        "issued_on": invoice.issued_on.isoformat(),
        "customer": invoice.customer.name,
        "state": normalise_state(typed_state).title(),
        "state_abbreviation": state_abbr(typed_state) if is_known_state(typed_state) else None,
        "gstin_state_code": state_code(invoice.customer.gstin),
        "lifecycle_status": invoice.status,
        "payment_status": invoice_status(invoice, PAYMENTS),
        "grand_total": _rupees(due),
        "amount_paid": _rupees(paid),
        "balance_due": _rupees(balance if balance > 0 else Decimal("0.00")),
    }


# ------------------------------------------------------------ the tools


def list_invoices(
    payment_status: Optional[str] = None,
    state: Optional[str] = None,
) -> Dict[str, Any]:
    """Every invoice, optionally narrowed by payment status or state."""
    rows = [_describe(invoice) for invoice in INVOICES]

    if payment_status:
        wanted = payment_status.strip().lower()
        if wanted == "pending":
            rows = [r for r in rows if r["payment_status"] in PENDING]
        else:
            rows = [r for r in rows if r["payment_status"] == wanted]

    if state:
        wanted_state = normalise_state(state)
        rows = [r for r in rows if normalise_state(r["state"]) == wanted_state]

    return {"count": len(rows), "invoices": rows}


def get_invoice(invoice_number: str) -> Dict[str, Any]:
    """One invoice with its full tax breakdown."""
    wanted = invoice_number.strip().upper()
    for invoice in INVOICES:
        if invoice.number.upper() == wanted:
            totals = compute_invoice(invoice)
            row = _describe(invoice)
            row["line_items"] = [
                {
                    "description": item.description,
                    "hsn": item.hsn,
                    "quantity": _rupees(item.quantity),
                    "unit_price": _rupees(item.unit_price),
                    "gst_rate_percent": str(item.gst_rate),
                    "discount_percent": str(item.discount_pct),
                }
                for item in invoice.items
            ]
            row.update(
                {
                    "gross": _rupees(totals["gross"]),
                    "discount": _rupees(totals["discount"]),
                    "taxable_value": _rupees(totals["taxable_value"]),
                    "cgst": _rupees(totals["cgst"]),
                    "sgst": _rupees(totals["sgst"]),
                    "igst": _rupees(totals["igst"]),
                    "round_off": _rupees(totals["round_off"]),
                }
            )
            return row

    known = ", ".join(i.number for i in INVOICES)
    return {"error": f"No invoice numbered {invoice_number!r}. Known invoices: {known}"}


def get_outstanding() -> Dict[str, Any]:
    """How much each customer still owes, cancelled invoices excluded."""
    owed = outstanding_by_customer(INVOICES, PAYMENTS)
    return {
        "outstanding": [
            {"customer": name, "amount_due": _rupees(amount)}
            for name, amount in sorted(owed.items())
        ],
        "total": _rupees(sum(owed.values(), Decimal("0.00"))),
    }


def lookup_state_abbreviation(state_name: str) -> Dict[str, Any]:
    """The two letter code for a state, matched ignoring case and spacing."""
    try:
        return {"state": normalise_state(state_name), "abbreviation": state_abbr(state_name)}
    except UnknownState as exc:
        return {"error": exc.args[0]}


# ------------------------------------------------- schemas and dispatch

TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "name": "list_invoices",
        "description": (
            "List invoices with their customer, state, lifecycle status "
            "(issued or cancelled), payment status (paid, part-paid, unpaid "
            "or cancelled) and balance due. Call with no arguments to see "
            "every invoice. Use this for questions about which invoices are "
            "pending, cancelled, or in a particular state."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "payment_status": {
                    "type": "string",
                    "enum": ["pending", "paid", "part-paid", "unpaid", "cancelled"],
                    "description": (
                        "Optional filter. 'pending' means unpaid or part-paid. "
                        "Omit to include every invoice."
                    ),
                },
                "state": {
                    "type": "string",
                    "description": "Optional state name filter, e.g. 'Gujarat'. Case insensitive.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_invoice",
        "description": (
            "Full detail for a single invoice: line items, CGST/SGST/IGST "
            "breakdown, discount, round off and amount paid."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "invoice_number": {
                    "type": "string",
                    "description": "The invoice number, e.g. 'INV-001'.",
                },
            },
            "required": ["invoice_number"],
        },
    },
    {
        "name": "get_outstanding",
        "description": (
            "Total still owed per customer, grouped by customer name. "
            "Cancelled invoices are excluded and customers who owe nothing "
            "are not listed."
        ),
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "lookup_state_abbreviation",
        "description": "The two letter abbreviation for an Indian state name, e.g. Gujarat is GJ.",
        "input_schema": {
            "type": "object",
            "properties": {
                "state_name": {"type": "string", "description": "The state name."},
            },
            "required": ["state_name"],
        },
    },
]

HANDLERS: Dict[str, Callable[..., Dict[str, Any]]] = {
    "list_invoices": list_invoices,
    "get_invoice": get_invoice,
    "get_outstanding": get_outstanding,
    "lookup_state_abbreviation": lookup_state_abbreviation,
}


def run_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Dispatch one tool call from the model.

    Bad names and bad arguments come back as an `error` result rather than an
    exception, because the model can read that and correct itself on the next
    turn, whereas a traceback just ends the conversation.
    """
    handler = HANDLERS.get(name)
    if handler is None:
        return {"error": f"Unknown tool {name!r}. Available: {', '.join(sorted(HANDLERS))}"}

    try:
        return handler(**(arguments or {}))
    except TypeError as exc:
        return {"error": f"Bad arguments for {name}: {exc}"}
