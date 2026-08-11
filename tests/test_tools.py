"""Tests for the tool layer the LLM calls into.

These run offline. The tools are the contract between the model and the
engine, so what matters is that they report the same facts the invoice
printout does.
"""

from decimal import Decimal

from billing.data import INVOICES, PAYMENTS
from billing.invoice import compute_invoice
from billing.reports import outstanding_by_customer
from billing.tools import (
    HANDLERS,
    TOOL_SCHEMAS,
    get_invoice,
    get_outstanding,
    list_invoices,
    lookup_state_abbreviation,
    run_tool,
)


def find(rows, number):
    return next(r for r in rows if r["invoice_number"] == number)


# ------------------------------------------------------------- schemas


def test_every_schema_has_a_handler():
    """A schema with no handler is a tool the model can call and never reach."""
    assert {s["name"] for s in TOOL_SCHEMAS} == set(HANDLERS)


def test_every_schema_is_well_formed():
    for schema in TOOL_SCHEMAS:
        assert schema["description"].strip()
        assert schema["input_schema"]["type"] == "object"
        for required in schema["input_schema"]["required"]:
            assert required in schema["input_schema"]["properties"], schema["name"]


# --------------------------------------------------------- list_invoices


def test_list_invoices_returns_every_invoice_by_default():
    result = list_invoices()
    assert result["count"] == len(INVOICES)


def test_cancelled_invoice_is_reported_as_cancelled():
    row = find(list_invoices()["invoices"], "INV-003")
    assert row["lifecycle_status"] == "cancelled"
    assert row["payment_status"] == "cancelled"


def test_pending_excludes_cancelled_and_paid():
    """'Pending' is the word a user says; it must never surface a cancelled invoice."""
    rows = list_invoices(payment_status="pending")["invoices"]
    statuses = {r["payment_status"] for r in rows}
    assert statuses <= {"unpaid", "part-paid"}
    assert "INV-003" not in {r["invoice_number"] for r in rows}


def test_part_paid_invoice_shows_its_balance():
    row = find(list_invoices()["invoices"], "INV-001")
    assert row["payment_status"] == "part-paid"
    assert row["amount_paid"] == "2000.00"
    assert row["balance_due"] == "1540.00"


def test_state_filter_ignores_the_case_it_was_typed_in():
    """Shah Enterprise has 'gujarat' in lower case in the sample data."""
    rows = list_invoices(state="GUJARAT")["invoices"]
    numbers = {r["invoice_number"] for r in rows}
    assert "INV-004" in numbers


def test_state_is_reported_tidily_whatever_was_typed():
    row = find(list_invoices()["invoices"], "INV-004")
    assert row["state"] == "Gujarat"
    assert row["state_abbreviation"] == "GJ"
    assert row["gstin_state_code"] == "24"


def test_totals_match_the_engine():
    """The model must never see a number the invoice printout disagrees with."""
    for row in list_invoices()["invoices"]:
        invoice = next(i for i in INVOICES if i.number == row["invoice_number"])
        assert row["grand_total"] == f"{compute_invoice(invoice)['grand_total']:.2f}"


# ----------------------------------------------------------- get_invoice


def test_get_invoice_includes_the_tax_breakdown():
    result = get_invoice("INV-002")
    assert result["igst"] == "359.64"
    assert result["cgst"] == "0.00"
    assert result["round_off"] == "0.36"
    assert len(result["line_items"]) == 1


def test_get_invoice_is_case_insensitive():
    assert get_invoice("inv-001")["invoice_number"] == "INV-001"


def test_unknown_invoice_returns_an_error_the_model_can_read():
    result = get_invoice("INV-999")
    assert "error" in result
    assert "INV-001" in result["error"]


# -------------------------------------------------------- get_outstanding


def test_outstanding_matches_the_report():
    engine = outstanding_by_customer(INVOICES, PAYMENTS)
    reported = {r["customer"]: r["amount_due"] for r in get_outstanding()["outstanding"]}
    assert reported == {name: f"{amount:.2f}" for name, amount in engine.items()}


def test_outstanding_excludes_cancelled_invoices():
    customers = {r["customer"] for r in get_outstanding()["outstanding"]}
    cancelled_only = {"Nova Systems"}  # INV-002 is unpaid, so Nova should appear
    assert cancelled_only <= customers


# -------------------------------------------------------------- dispatch


def test_lookup_state_abbreviation_normalises():
    assert lookup_state_abbreviation("  gujarat ")["abbreviation"] == "GJ"


def test_lookup_state_abbreviation_reports_unknown_as_error():
    assert "error" in lookup_state_abbreviation("Atlantis")


def test_run_tool_dispatches_by_name():
    assert run_tool("get_outstanding", {})["outstanding"]


def test_run_tool_reports_an_unknown_tool_instead_of_raising():
    result = run_tool("delete_everything", {})
    assert "error" in result
    assert "list_invoices" in result["error"]


def test_run_tool_reports_bad_arguments_instead_of_raising():
    """The model can recover from an error result; it cannot recover from a traceback."""
    result = run_tool("get_invoice", {"wrong_argument": "x"})
    assert "error" in result


def test_run_tool_accepts_no_arguments():
    assert run_tool("list_invoices", {})["count"] == len(INVOICES)


def test_amounts_are_strings_not_floats():
    """A float in the JSON would hand the model a value that has lost paise."""
    for row in list_invoices()["invoices"]:
        assert isinstance(row["grand_total"], str)
        assert not isinstance(row["grand_total"], float)
        Decimal(row["grand_total"])  # parses cleanly
