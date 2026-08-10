# aiguru-billing-workshop

A small GST billing engine, used as the working codebase in the AI Guru
agentic engineering workshop.

It issues invoices, applies Indian GST, records payments, and reports
outstanding amounts. There is no database and no web server — everything runs
from sample data in memory.

## Before the session

Nothing here is required. The session is follow-along — the facilitator drives
on the main screen and you are welcome to simply watch. Everyone gets this
repo, and it works just as well at 11pm on your own machine.

If you do want to follow along on a laptop:

1. Python 3.10 or newer. Check with `python --version` (or `python3`, or `py`).
2. Claude Code installed and signed in — https://claude.com/claude-code
   Do this the night before, not in the hall. First-time sign-in needs network.
3. Clone this repo and confirm it runs:

   ```bash
   git clone https://github.com/AIGuruOne/aiguru-billing-workshop
   cd aiguru-billing-workshop
   python check.py      # expect: 15 passed, 1 failed
   ```

That one failure is on purpose. Finding and fixing it is the first exercise.

## Getting started

You need Python 3.10 or newer. The billing engine itself needs nothing
installed.

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
