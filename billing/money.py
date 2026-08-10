"""Money helpers.

All monetary values in this project are Decimal, never float.
Floats cannot represent 0.10 exactly and paise drift shows up in invoices.
"""

from decimal import Decimal, ROUND_HALF_UP

PAISE = Decimal("0.01")
RUPEE = Decimal("1")


def money(value) -> Decimal:
    """Convert any number-like value into a Decimal rounded to paise."""
    return Decimal(str(value)).quantize(PAISE, rounding=ROUND_HALF_UP)


def to_paise(value: Decimal) -> Decimal:
    """Round an existing Decimal to two places."""
    return value.quantize(PAISE, rounding=ROUND_HALF_UP)


def to_rupee(value: Decimal) -> Decimal:
    """Round an existing Decimal to the nearest whole rupee."""
    return value.quantize(RUPEE, rounding=ROUND_HALF_UP)
