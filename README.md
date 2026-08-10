# aiguru-billing-workshop

A small GST billing engine, used as the working codebase in the AI Guru
agentic engineering workshop.

It issues invoices, applies Indian GST, records payments, and reports
outstanding amounts. There is no database and no web server — everything runs
from sample data in memory.

## Getting started

You need Python 3.10 or newer. Nothing else. There is nothing to install.

```bash
python run_demo.py        # print the sample invoices
python check.py           # run the checks
```

If `python` is not found, try `python3` or `py` — one of the three will work
on your machine.

If you already have pytest, `python -m pytest -q` runs the same checks.

## Where things live

- `SPEC.md` — the product brief the code was written from
- `CLAUDE.md` — the coding standards an AI agent reads before making changes
- `billing/` — the engine
- `check.py` — runs every check, standard library only
- `tests/` — the same checks as a pytest suite

## Resetting

If you cloned with git, `git checkout .` puts everything back.

If you downloaded the ZIP, there is no git history — delete the folder and
extract the ZIP again.

## A note on the tests

One check fails when you first open this. That is on purpose. Finding it and
fixing it is the first exercise of the session.

Fix the code, not the check.
