"""Tests for the GST split."""

from decimal import Decimal

from billing.gst import is_interstate, split_gst, state_code


def test_state_code_is_first_two_digits_of_gstin():
    assert state_code("24AAACA1234A1Z5") == "24"
    assert state_code("27AAACN5678B1Z9") == "27"


def test_same_state_splits_into_cgst_and_sgst():
    tax = split_gst(Decimal("1000.00"), Decimal("18"), interstate=False)
    assert tax["cgst"] == Decimal("90.00")
    assert tax["sgst"] == Decimal("90.00")
    assert tax["igst"] == Decimal("0.00")


def test_other_state_charges_igst_only():
    tax = split_gst(Decimal("1000.00"), Decimal("18"), interstate=True)
    assert tax["cgst"] == Decimal("0.00")
    assert tax["sgst"] == Decimal("0.00")
    assert tax["igst"] == Decimal("180.00")


def test_odd_paise_split_does_not_lose_money():
    """When the tax cannot be halved exactly, the two halves must still add up."""
    tax = split_gst(Decimal("333.33"), Decimal("5"), interstate=False)
    assert tax["cgst"] + tax["sgst"] == Decimal("16.67")


def test_customer_in_seller_state_is_intrastate():
    assert is_interstate("Gujarat", "Gujarat") is False


def test_customer_in_another_state_is_interstate():
    assert is_interstate("Gujarat", "Maharashtra") is True
