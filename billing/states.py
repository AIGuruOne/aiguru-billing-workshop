"""Lookup of state codes from the table in states.json.

The table is data, not code, so it lives in a JSON file that a non-programmer
can edit without touching the engine. It is read once and cached — the file is
small, but a lookup happens per invoice line and re-reading it each time would
be wasteful.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict

STATES_PATH = Path(__file__).parent / "states.json"


class UnknownState(KeyError):
    """Raised when a state name is not in the table.

    A subclass of KeyError so existing `except KeyError` handlers still catch
    it, but it carries a message naming the state that failed.
    """


@lru_cache(maxsize=1)
def load_states() -> Dict[str, str]:
    """Return the whole state table, keyed by state name as written in the file."""
    with STATES_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def normalise_state(state_name: str) -> str:
    """Fold a typed state name to the form used as a key in the table.

    State names reach us as free text typed by whoever created the customer
    record, so "gujarat", "Gujarat" and " GUJARAT " are the same state. Case
    and runs of whitespace are the differences that actually show up; anything
    beyond that is a genuinely different name and should not be guessed at.
    """
    return " ".join(state_name.split()).upper()


@lru_cache(maxsize=1)
def _normalised_index() -> Dict[str, str]:
    """The table re-keyed by normalised name.

    Built from the file rather than assumed, so the lookup still works if
    someone hand-edits states.json with a differently cased key.
    """
    return {normalise_state(name): abbr for name, abbr in load_states().items()}


def state_abbr(state_name: str) -> str:
    """Return the two letter code for a state name.

    Matching ignores case and extra whitespace. An unrecognised name raises
    rather than returning a default — a wrong state silently becomes the wrong
    tax on a real invoice.
    """
    try:
        return _normalised_index()[normalise_state(state_name)]
    except KeyError:
        raise UnknownState(
            f"{state_name!r} is not in {STATES_PATH.name}. "
            f"Known states: {', '.join(sorted(load_states()))}"
        ) from None


def is_known_state(state_name: str) -> bool:
    """Return True when the state name is in the table, ignoring case."""
    return normalise_state(state_name) in _normalised_index()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        for name, abbr in sorted(load_states().items()):
            print(f"  {abbr}   {name}")
        sys.exit(0)

    try:
        print(state_abbr(" ".join(sys.argv[1:])))
    except UnknownState as exc:
        print(exc.args[0], file=sys.stderr)
        sys.exit(1)
