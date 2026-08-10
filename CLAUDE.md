# Working in this repository

Read this before making any change.

## What this project is

A GST billing engine. The product brief lives in `SPEC.md`. If the brief and
the code disagree, the brief wins — but say so rather than silently changing
behaviour.

## Layout

```
billing/money.py      Decimal helpers. Every rupee value passes through here.
billing/models.py     Customer, LineItem, Invoice, Payment. Data only, no logic.
billing/gst.py        Deciding the tax type and splitting the tax.
billing/invoice.py    Adding an invoice up.
billing/reports.py    Anything that reads across many invoices.
billing/data.py       Sample records so the app runs without a database.
tests/                One test file per module in billing/.
run_demo.py           Prints every sample invoice. No database, no arguments.
```

## Rules

**Money is always `Decimal`, never `float`.** A float cannot hold 0.10 exactly
and the error surfaces as missing paise on real invoices. Build Decimals from
strings, not from floats.

**Round at the boundary, not in the middle.** Use the helpers in `money.py`.
Rounding the same value twice quietly loses money.

**Every behaviour change needs a test.** A change with no test is not finished.

**Tests are written against the brief, not against the current code.** If a
test would only pass because of how the code happens to work today, it is the
wrong test.

**Standard library plus pytest only.** No new dependencies. This has to run on
a laptop with no internet.

## Conventions

- Python 3.10 or newer.
- Type hints on anything public.
- Docstrings explain *why*, not *what*. The code already says what.
- Function names read as statements: `is_interstate`, `amount_paid`.

## Do not touch

- `SPEC.md` — that is the customer's document, not ours.
- Sample data in `billing/data.py`, unless the task is specifically about it.
- Test files, unless the task is specifically about tests. Fix the code so the
  test passes. Do not change the test so the code passes.

## Running things

```
python3 -m pytest -q      Run every test.
python3 run_demo.py       Print the sample invoices.
```
