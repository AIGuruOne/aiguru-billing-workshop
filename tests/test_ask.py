"""Tests for the question-answering loop.

Every test here uses a fake transport. Nothing in this file touches the
network or needs an API key — the loop is what is under test, not the model.
"""

import json

import pytest

from billing.ask import AskError, ask


def scripted(*responses):
    """A transport that replays canned API responses and records the requests."""
    sent = []

    def transport(payload):
        sent.append(payload)
        return responses[len(sent) - 1]

    transport.sent = sent
    return transport


def text(body):
    return {"content": [{"type": "text", "text": body}]}


def calls(name, arguments, block_id="tu_1"):
    return {
        "content": [{"type": "tool_use", "id": block_id, "name": name, "input": arguments}]
    }


def test_a_plain_answer_comes_straight_back():
    transport = scripted(text("Two invoices are pending."))
    assert ask("what is pending?", transport=transport) == "Two invoices are pending."


def test_the_question_and_tools_are_sent():
    transport = scripted(text("ok"))
    ask("what is pending?", transport=transport)
    payload = transport.sent[0]
    assert payload["messages"][0] == {"role": "user", "content": "what is pending?"}
    assert {t["name"] for t in payload["tools"]} >= {"list_invoices", "get_outstanding"}
    assert "pending" in payload["system"]


def test_a_tool_call_is_executed_and_fed_back():
    transport = scripted(
        calls("list_invoices", {"payment_status": "pending"}),
        text("INV-001 and INV-002 are pending."),
    )
    answer = ask("which are pending?", transport=transport)
    assert answer == "INV-001 and INV-002 are pending."

    followup = transport.sent[1]["messages"]
    assert followup[1]["role"] == "assistant"

    result_block = followup[2]["content"][0]
    assert result_block["type"] == "tool_result"
    assert result_block["tool_use_id"] == "tu_1"

    # The tool actually ran against the engine, not a stub.
    payload = json.loads(result_block["content"])
    assert payload["count"] >= 1
    assert all(r["payment_status"] in ("unpaid", "part-paid") for r in payload["invoices"])


def test_several_tool_calls_in_one_turn_all_run():
    transport = scripted(
        {
            "content": [
                {"type": "tool_use", "id": "a", "name": "get_outstanding", "input": {}},
                {
                    "type": "tool_use",
                    "id": "b",
                    "name": "lookup_state_abbreviation",
                    "input": {"state_name": "gujarat"},
                },
            ]
        },
        text("done"),
    )
    ask("tell me everything", transport=transport)

    results = transport.sent[1]["messages"][2]["content"]
    assert [r["tool_use_id"] for r in results] == ["a", "b"]
    assert json.loads(results[1]["content"])["abbreviation"] == "GJ"


def test_a_bad_tool_name_is_returned_to_the_model_not_raised():
    """The model gets a chance to correct itself rather than the run dying."""
    transport = scripted(
        calls("no_such_tool", {}),
        text("Sorry, let me try again."),
    )
    assert ask("hm", transport=transport) == "Sorry, let me try again."
    result = transport.sent[1]["messages"][2]["content"][0]
    assert "error" in json.loads(result["content"])


def test_an_api_error_response_raises():
    transport = scripted({"type": "error", "error": {"message": "overloaded"}})
    with pytest.raises(AskError, match="overloaded"):
        ask("anything", transport=transport)


def test_a_loop_that_never_settles_gives_up():
    """Without a cap, a model that keeps calling tools would run forever."""
    transport = scripted(*[calls("get_outstanding", {}, block_id=f"t{i}") for i in range(20)])
    with pytest.raises(AskError, match="Gave up"):
        ask("spin", transport=transport)


def test_a_missing_api_key_is_a_clear_message(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(AskError, match="ANTHROPIC_API_KEY"):
        ask("anything")
