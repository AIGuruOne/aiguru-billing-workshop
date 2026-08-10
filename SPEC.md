# Billing engine — product specification

A small billing engine for an Indian services and trading business.
It issues GST invoices, records payments, and reports who still owes money.

This document is the brief. It is what a developer — human or AI — is given
before writing any code.

---

## 1. Customers

Every customer has a name, a GSTIN, and a state.

A GSTIN is 15 characters. The first two digits are the state code issued by the
GST department. Gujarat is 24, Maharashtra is 27.

## 2. Invoices

An invoice has a number, a date, one customer, and one or more line items.

A line item has a description, an HSN or SAC code, a quantity, a unit price,
and a GST rate expressed as a whole percent.

An invoice is either `issued` or `cancelled`.

## 3. Tax

Indian GST is charged differently depending on whether the sale crosses a state
border.

- **Within our own state** — the tax is split in half: CGST and SGST.
- **Into another state** — the whole amount is charged as IGST.

A sale is inter-state when the customer is in a different state from us.

GST is charged at the rate applicable to each line item.

When the tax cannot be divided into two equal halves, the two halves must still
add up to the full tax. No paise may be lost.

## 4. Discounts

A line item may carry a percentage discount.

The discount is shown on the invoice as its own line, and it reduces what the
customer pays.

## 5. Rounding

Money is held to two decimal places throughout.

The final invoice total is rounded to the nearest whole rupee. The difference
between the unrounded total and the rounded total is shown on the invoice as
**Round Off**, so the customer can see the adjustment.

## 6. Payments

A payment records an invoice number, a date, and an amount.

An invoice may receive several payments. An invoice is `paid` once payments
reach the invoice total, `part-paid` if something has been received but not the
whole amount, and `unpaid` if nothing has been received.

## 7. Outstanding report

The outstanding report shows how much each customer still owes, grouped by
customer name.

Cancelled invoices are not included. Customers who owe nothing are not listed.
