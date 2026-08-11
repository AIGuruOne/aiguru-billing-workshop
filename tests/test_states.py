"""Tests for the state code lookup."""

import pytest

from billing.states import (
    UnknownState,
    is_known_state,
    load_states,
    normalise_state,
    state_abbr,
)


def test_lookup_returns_the_two_letter_code():
    assert state_abbr("GUJARAT") == "GJ"
    assert state_abbr("RAJASTHAN") == "RJ"
    assert state_abbr("MAHARASHTRA") == "MH"


def test_table_covers_at_least_ten_states():
    assert len(load_states()) >= 10


def test_every_code_is_two_upper_case_letters():
    for name, abbr in load_states().items():
        assert len(abbr) == 2, name
        assert abbr.isupper(), name


def test_codes_are_unique():
    """Two states sharing a code would make the table ambiguous to read back."""
    codes = list(load_states().values())
    assert len(codes) == len(set(codes))


def test_lookup_ignores_case():
    """Customer records carry the state as free text, in whatever case."""
    for typed in ("gujarat", "Gujarat", "GUJARAT", "GuJaRaT"):
        assert state_abbr(typed) == "GJ"


def test_lookup_ignores_surrounding_and_repeated_whitespace():
    assert state_abbr("  tamil nadu  ") == "TN"
    assert state_abbr("tamil\tnadu") == "TN"
    assert state_abbr("TAMIL   NADU") == "TN"


def test_normalise_folds_case_and_whitespace():
    assert normalise_state("  tamil   nadu ") == "TAMIL NADU"


def test_normalise_is_idempotent():
    """Normalising an already normalised name must not change it again."""
    for name in load_states():
        assert normalise_state(normalise_state(name)) == normalise_state(name)


def test_normalising_does_not_invent_matches():
    """Folding case is not licence to guess at a name we do not hold."""
    for wrong in ("gujrat", "guj", "west  bangal", ""):
        with pytest.raises(UnknownState):
            state_abbr(wrong)


def test_unknown_state_names_the_state_it_could_not_find():
    with pytest.raises(UnknownState) as caught:
        state_abbr("ATLANTIS")
    assert "ATLANTIS" in caught.value.args[0]


def test_unknown_state_is_a_key_error():
    """Callers already catching KeyError keep working."""
    assert issubclass(UnknownState, KeyError)


def test_is_known_state_does_not_raise():
    assert is_known_state("GUJARAT") is True
    assert is_known_state("gujarat") is True
    assert is_known_state("ATLANTIS") is False


def test_normalised_keys_stay_unique():
    """Two keys folding to the same name would make the table ambiguous."""
    names = list(load_states())
    assert len({normalise_state(n) for n in names}) == len(names)
