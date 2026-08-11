"""Run every check in this project using nothing but the standard library.

    python check.py        (or: python3 check.py)

You do not need pytest, pip, or an internet connection.
If you already have pytest, `python -m pytest -q` runs the same checks.
"""

import json
import sys
import traceback
from datetime import date
from decimal import Decimal

from billing.ask import AskError, ask
from billing.data import INVOICES
from billing.gst import is_interstate, split_gst, state_code
from billing.invoice import compute_invoice
from billing.models import Customer, Invoice, LineItem, Payment
from billing.reports import amount_paid, invoice_status, outstanding_by_customer
from billing.states import (
    UnknownState,
    is_known_state,
    load_states,
    normalise_state,
    state_abbr,
)
from billing.tools import (
    HANDLERS,
    TOOL_SCHEMAS,
    get_invoice,
    list_invoices,
    run_tool,
)

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


# ------------------------------------------------------------- STATES


@check("state lookup returns the two letter code")
def _():
    assert state_abbr("GUJARAT") == "GJ"
    assert state_abbr("RAJASTHAN") == "RJ"
    assert state_abbr("MAHARASHTRA") == "MH"


@check("state table covers at least ten states")
def _():
    assert len(load_states()) >= 10


@check("every state code is two upper case letters")
def _():
    for name, abbr in load_states().items():
        assert len(abbr) == 2, name
        assert abbr.isupper(), name


@check("state codes are unique")
def _():
    codes = list(load_states().values())
    assert len(codes) == len(set(codes))


@check("state lookup ignores case")
def _():
    for typed in ("gujarat", "Gujarat", "GUJARAT", "GuJaRaT"):
        assert state_abbr(typed) == "GJ"


@check("state lookup ignores extra whitespace")
def _():
    assert state_abbr("  tamil nadu  ") == "TN"
    assert state_abbr("TAMIL   NADU") == "TN"


@check("normalising folds case and whitespace, and is idempotent")
def _():
    assert normalise_state("  tamil   nadu ") == "TAMIL NADU"
    for name in load_states():
        assert normalise_state(normalise_state(name)) == normalise_state(name)


@check("normalised keys stay unique")
def _():
    names = list(load_states())
    assert len({normalise_state(n) for n in names}) == len(names)


@check("normalising does not invent matches")
def _():
    for wrong in ("gujrat", "guj", "west  bangal", ""):
        try:
            state_abbr(wrong)
        except UnknownState:
            continue
        raise AssertionError(f"expected UnknownState for {wrong!r}")


@check("unknown state is still a KeyError")
def _():
    assert issubclass(UnknownState, KeyError)
    assert is_known_state("gujarat") is True
    assert is_known_state("ATLANTIS") is False


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


# -------------------------------------------------------------- TOOLS


@check("every tool schema has a handler")
def _():
    assert {s["name"] for s in TOOL_SCHEMAS} == set(HANDLERS)


@check("every tool schema is well formed")
def _():
    for schema in TOOL_SCHEMAS:
        assert schema["description"].strip()
        assert schema["input_schema"]["type"] == "object"
        for required in schema["input_schema"]["required"]:
            assert required in schema["input_schema"]["properties"], schema["name"]


@check("pending excludes cancelled and paid invoices")
def _():
    rows = list_invoices(payment_status="pending")["invoices"]
    assert {r["payment_status"] for r in rows} <= {"unpaid", "part-paid"}
    assert "INV-003" not in {r["invoice_number"] for r in rows}


@check("cancelled invoice is reported as cancelled")
def _():
    rows = list_invoices()["invoices"]
    row = next(r for r in rows if r["invoice_number"] == "INV-003")
    assert row["lifecycle_status"] == "cancelled"
    assert row["payment_status"] == "cancelled"


@check("state filter and display ignore how the state was typed")
def _():
    rows = list_invoices(state="GUJARAT")["invoices"]
    assert "INV-004" in {r["invoice_number"] for r in rows}
    row = next(r for r in rows if r["invoice_number"] == "INV-004")
    assert row["state"] == "Gujarat"
    assert row["state_abbreviation"] == "GJ"
    assert row["gstin_state_code"] == "24"


@check("tool totals match the engine")
def _():
    for row in list_invoices()["invoices"]:
        invoice = next(i for i in INVOICES if i.number == row["invoice_number"])
        assert row["grand_total"] == f"{compute_invoice(invoice)['grand_total']:.2f}"
        assert isinstance(row["grand_total"], str)


@check("unknown tool and bad arguments come back as errors, not tracebacks")
def _():
    assert "error" in run_tool("delete_everything", {})
    assert "error" in run_tool("get_invoice", {"wrong_argument": "x"})
    assert "error" in get_invoice("INV-999")


# ---------------------------------------------------------------- ASK


def scripted(*responses):
    """A fake transport replaying canned API responses. No network, no key."""
    sent = []

    def transport(payload):
        sent.append(payload)
        return responses[len(sent) - 1]

    transport.sent = sent
    return transport


@check("a plain answer comes straight back")
def _():
    transport = scripted({"content": [{"type": "text", "text": "Two are pending."}]})
    assert ask("what is pending?", transport=transport) == "Two are pending."


@check("a tool call is executed and fed back to the model")
def _():
    transport = scripted(
        {"content": [{"type": "tool_use", "id": "tu_1",
                      "name": "list_invoices", "input": {"payment_status": "pending"}}]},
        {"content": [{"type": "text", "text": "INV-001 and INV-002."}]},
    )
    assert ask("which are pending?", transport=transport) == "INV-001 and INV-002."

    result = transport.sent[1]["messages"][2]["content"][0]
    assert result["type"] == "tool_result"
    assert result["tool_use_id"] == "tu_1"
    payload = json.loads(result["content"])
    assert all(r["payment_status"] in ("unpaid", "part-paid") for r in payload["invoices"])


@check("a bad tool name is returned to the model, not raised")
def _():
    transport = scripted(
        {"content": [{"type": "tool_use", "id": "a", "name": "no_such_tool", "input": {}}]},
        {"content": [{"type": "text", "text": "Let me try again."}]},
    )
    assert ask("hm", transport=transport) == "Let me try again."
    result = transport.sent[1]["messages"][2]["content"][0]
    assert "error" in json.loads(result["content"])


@check("an api error raises")
def _():
    transport = scripted({"type": "error", "error": {"message": "overloaded"}})
    try:
        ask("anything", transport=transport)
    except AskError as exc:
        assert "overloaded" in str(exc)
    else:
        raise AssertionError("expected AskError")


@check("a loop that never settles gives up")
def _():
    transport = scripted(
        *[{"content": [{"type": "tool_use", "id": f"t{i}",
                        "name": "get_outstanding", "input": {}}]} for i in range(20)]
    )
    try:
        ask("spin", transport=transport)
    except AskError as exc:
        assert "Gave up" in str(exc)
    else:
        raise AssertionError("expected AskError")


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
