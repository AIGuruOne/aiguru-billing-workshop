"""GST calculation.

Indian GST splits differently depending on whether a sale crosses a state border:

  Same state      ->  CGST (half the rate) + SGST (half the rate)
  Different state ->  IGST (the full rate)

The place of supply is decided by the state, and the authoritative record of a
customer's state is the first two digits of their GSTIN, not the state name
someone typed into the customer record.
"""

from decimal import Decimal

from .money import to_paise

SELLER_GSTIN = "24AABCU9603R1ZM"
SELLER_STATE = "Gujarat"


def state_code(gstin: str) -> str:
    """Return the two digit state code from a GSTIN."""
    return gstin[:2]


def is_interstate(seller_state: str, buyer_state: str) -> bool:
    """Return True when the sale crosses a state border."""
    return seller_state != buyer_state


def split_gst(taxable_value: Decimal, gst_rate: Decimal, interstate: bool) -> dict:
    """Split a taxable value into its CGST / SGST / IGST components."""
    total_tax = to_paise(taxable_value * gst_rate / Decimal("100"))

    if interstate:
        return {
            "cgst": Decimal("0.00"),
            "sgst": Decimal("0.00"),
            "igst": total_tax,
        }

    half = to_paise(total_tax / Decimal("2"))
    return {
        "cgst": half,
        "sgst": total_tax - half,
        "igst": Decimal("0.00"),
    }
