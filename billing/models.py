"""Data models for customers, invoices and payments."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import List

from .money import money


@dataclass
class Customer:
    name: str
    gstin: str          # 15 characters. First two digits are the state code.
    state: str          # Human readable state name, as typed by whoever created the record.


@dataclass
class LineItem:
    description: str
    hsn: str            # HSN/SAC code for the goods or service.
    quantity: Decimal
    unit_price: Decimal
    gst_rate: Decimal   # Whole percent. 18 means 18%.
    discount_pct: Decimal = Decimal("0")

    def __post_init__(self):
        self.quantity = money(self.quantity)
        self.unit_price = money(self.unit_price)
        self.gst_rate = Decimal(str(self.gst_rate))
        self.discount_pct = Decimal(str(self.discount_pct))


@dataclass
class Invoice:
    number: str
    issued_on: date
    customer: Customer
    items: List[LineItem] = field(default_factory=list)
    status: str = "issued"      # issued | cancelled


@dataclass
class Payment:
    invoice_number: str
    received_on: date
    amount: Decimal

    def __post_init__(self):
        self.amount = money(self.amount)
